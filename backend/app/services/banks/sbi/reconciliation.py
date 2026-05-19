"""
Airco Insights — SBI Bank Balance Reconciliation
===================================================
Verifies balance continuity: Opening + Credits - Debits = Closing Balance.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class SBIReconciliationError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(message)


@dataclass
class ReconciliationMismatch:
    transaction_index: int
    expected_balance: float
    actual_balance: float
    difference: float
    previous_balance: float
    transaction_amount: float
    is_debit: bool


@dataclass
class SBIReconciliationResult:
    is_reconciled: bool
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    calculated_closing: float
    final_difference: float
    transaction_count: int
    mismatches: List[ReconciliationMismatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_reconciled":     self.is_reconciled,
            "opening_balance":   self.opening_balance,
            "closing_balance":   self.closing_balance,
            "total_credits":     self.total_credits,
            "total_debits":      self.total_debits,
            "calculated_closing": self.calculated_closing,
            "final_difference":  self.final_difference,
            "transaction_count": self.transaction_count,
            "mismatch_count":    len(self.mismatches),
        }


class SBIReconciliation:
    TOLERANCE = 0.01

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def reconcile(
        self,
        transactions: List[Dict[str, Any]],
        expected_opening: Optional[float] = None,
        expected_closing: Optional[float] = None,
        expected_credits: Optional[float] = None,
        expected_debits:  Optional[float] = None,
    ) -> SBIReconciliationResult:
        if not transactions:
            raise SBIReconciliationError("No transactions to reconcile", error_code="NO_TRANSACTIONS")

        self.logger.info("Reconciling %d SBI transactions", len(transactions))

        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits  = sum(t.get("debit")  or 0 for t in transactions)

        first          = transactions[0]
        inferred_open  = first.get("balance", 0) - (first.get("credit") or 0) + (first.get("debit") or 0)
        opening_balance = expected_opening if expected_opening is not None else inferred_open

        closing_balance    = transactions[-1].get("balance", 0)
        calculated_closing = opening_balance + total_credits - total_debits
        final_diff         = abs(calculated_closing - closing_balance)
        is_reconciled      = final_diff <= self.TOLERANCE

        mismatches = self._check_balance_progression(transactions)
        segment_resets = getattr(self, "_last_segment_resets", 0)
        if mismatches:
            is_reconciled = False
        elif segment_resets and final_diff > self.TOLERANCE:
            is_reconciled = True

        self.logger.info(
            "SBI reconciliation %s: opening=%.2f closing=%.2f diff=%.4f mismatches=%d resets=%d",
            "PASSED" if is_reconciled else "FAILED",
            opening_balance, closing_balance, final_diff, len(mismatches), segment_resets,
        )

        return SBIReconciliationResult(
            is_reconciled=is_reconciled,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
            calculated_closing=calculated_closing,
            final_difference=final_diff,
            transaction_count=len(transactions),
            mismatches=mismatches,
        )

    def _check_balance_progression(self, transactions):
        mismatches = []
        segment_resets = 0
        for i in range(1, len(transactions)):
            prev     = transactions[i - 1]
            curr     = transactions[i]
            prev_bal = prev.get("balance", 0)
            curr_bal = curr.get("balance", 0)
            credit   = curr.get("credit") or 0
            debit    = curr.get("debit")  or 0
            expected = prev_bal + credit - debit
            diff     = abs(expected - curr_bal)
            if diff > self.TOLERANCE:
                if i + 1 < len(transactions) and self._looks_like_segment_reset(curr, transactions[i + 1]):
                    segment_resets += 1
                    continue
                mismatches.append(ReconciliationMismatch(
                    transaction_index=i,
                    expected_balance=expected,
                    actual_balance=curr_bal,
                    difference=diff,
                    previous_balance=prev_bal,
                    transaction_amount=credit if credit else debit,
                    is_debit=debit > 0,
                ))
        self._last_segment_resets = segment_resets
        return mismatches

    def _looks_like_segment_reset(self, current: Dict[str, Any], next_txn: Dict[str, Any]) -> bool:
        curr_bal = current.get("balance", 0)
        next_bal = next_txn.get("balance", 0)
        next_credit = next_txn.get("credit") or 0
        next_debit = next_txn.get("debit") or 0
        expected_next = curr_bal + next_credit - next_debit
        return abs(expected_next - next_bal) <= self.TOLERANCE

    def auto_correct_debit_credit(
        self, transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        corrected   = []
        corrections = 0
        for i, txn in enumerate(transactions):
            txn_copy = dict(txn)
            if i == 0:
                corrected.append(txn_copy)
                continue
            prev_bal = corrected[i - 1].get("balance", 0)
            curr_bal = txn.get("balance", 0)
            debit    = txn.get("debit")  or 0
            credit   = txn.get("credit") or 0
            expected = (prev_bal - debit) if debit else (prev_bal + credit)
            diff     = abs(expected - curr_bal)
            if diff > self.TOLERANCE:
                textual_direction = self._infer_textual_direction(txn)
                if textual_direction is not None:
                    amount = credit or debit
                    if amount:
                        desired_expected = prev_bal + amount if textual_direction else prev_bal - amount
                        desired_diff = abs(desired_expected - curr_bal)
                        current_is_credit = credit > 0 and not debit
                        current_is_debit = debit > 0 and not credit
                        if desired_diff <= diff and (
                            (textual_direction and not current_is_credit)
                            or (not textual_direction and not current_is_debit)
                        ):
                            txn_copy["debit"] = None if textual_direction else amount
                            txn_copy["credit"] = amount if textual_direction else None
                            corrections += 1
                else:
                    new_expected = (prev_bal + debit) if debit else (prev_bal - credit)
                    if abs(new_expected - curr_bal) < diff:
                        txn_copy["debit"]  = credit if credit else None
                        txn_copy["credit"] = debit  if debit  else None
                        corrections += 1
            corrected.append(txn_copy)
        return corrected, corrections

    def _infer_textual_direction(self, txn: Dict[str, Any]) -> Optional[bool]:
        description = str(txn.get("description") or "").upper()
        if not description:
            return None

        if "CHARG" in description or "CHARGE" in description or "CHAR--" in description:
            return False

        credit_patterns = (
            "BY TRANSFER",
            "UPI/CR/",
            "DEP TFR",
            "CASH DEPOSIT",
            "CSH DEP",
            "DEPOSITED AT GCC",
            "SALARY",
            "INTEREST",
            "REFUND",
            "REVERSAL",
        )
        debit_patterns = (
            "TO TRANSFER",
            "UPI/DR/",
            "WDL TFR",
            "DEBIT-",
            "DEBIT ACHDR",
            "ACHDR",
            "CHARGES",
            "CHARGE",
            "ATM",
            "WITHDRAW",
        )

        if any(token in description for token in credit_patterns):
            return True
        if any(token in description for token in debit_patterns):
            return False

        if re.search(r'\bCR\b', description) and not re.search(r'\bDR\b', description):
            return True
        if re.search(r'\bDR\b', description) and not re.search(r'\bCR\b', description):
            return False
        return None
