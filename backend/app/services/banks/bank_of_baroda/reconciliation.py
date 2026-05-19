"""
Airco Insights - Bank of Baroda Reconciliation
"""

import logging
from typing import Dict, List, Optional

from app.services.banks._shared.generic_bank import GenericReconciliation, GenericReconciliationError

logger = logging.getLogger(__name__)


class BankOfBarodaReconciliation(GenericReconciliation):
    def __init__(self, strict_mode: bool = False):
        super().__init__(strict_mode=strict_mode)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.tolerance = 0.01

    def reconcile(
        self,
        transactions: List[Dict],
        expected_opening: Optional[float] = None,
        expected_closing: Optional[float] = None,
    ) -> Dict:
        result = {
            "passed": True,
            "opening_balance": expected_opening or 0,
            "closing_balance": expected_closing or 0,
            "calculated_opening": None,
            "calculated_closing": None,
            "mismatches": [],
            "corrections": 0,
        }

        if not transactions:
            result["passed"] = False
            return result

        # Calculate opening balance from first transaction
        first_txn = transactions[0]
        debit = first_txn.get("debit") or 0
        credit = first_txn.get("credit") or 0
        balance = first_txn.get("balance") or 0
        calculated_opening = balance - credit + debit
        result["calculated_opening"] = round(calculated_opening, 2)

        # Use expected opening if provided, otherwise use calculated
        opening_balance = expected_opening if expected_opening is not None else calculated_opening
        result["opening_balance"] = round(opening_balance, 2)

        # Verify opening balance
        if expected_opening is not None:
            diff = abs(calculated_opening - expected_opening)
            if diff > self.tolerance:
                result["passed"] = False
                result["mismatches"].append({
                    "type": "opening_balance",
                    "expected": expected_opening,
                    "calculated": calculated_opening,
                    "difference": diff,
                })

        # Calculate closing balance from last transaction
        last_txn = transactions[-1]
        result["calculated_closing"] = round(last_txn.get("balance", 0), 2)

        # Verify closing balance
        if expected_closing is not None:
            diff = abs(result["calculated_closing"] - expected_closing)
            if diff > self.tolerance:
                result["passed"] = False
                result["mismatches"].append({
                    "type": "closing_balance",
                    "expected": expected_closing,
                    "calculated": result["calculated_closing"],
                    "difference": diff,
                })
            result["closing_balance"] = round(expected_closing, 2)
        else:
            result["closing_balance"] = result["calculated_closing"]

        # Verify balance continuity
        current_balance = opening_balance
        for i, txn in enumerate(transactions):
            debit = txn.get("debit") or 0
            credit = txn.get("credit") or 0
            expected_balance = current_balance - debit + credit
            actual_balance = txn.get("balance") or 0

            diff = abs(expected_balance - actual_balance)
            if diff > self.tolerance:
                result["passed"] = False
                result["mismatches"].append({
                    "type": "balance_continuity",
                    "index": i,
                    "date": txn.get("date"),
                    "expected": expected_balance,
                    "actual": actual_balance,
                    "difference": diff,
                })

            current_balance = actual_balance

        return result


# Re-export for compatibility
BankOfBarodaReconciliationError = GenericReconciliationError
