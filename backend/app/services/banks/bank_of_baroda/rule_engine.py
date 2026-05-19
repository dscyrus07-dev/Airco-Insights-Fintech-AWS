"""
Airco Insights - Bank of Baroda Rule Engine
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

from app.services.banks._shared.category_registry import normalize_category
from app.services.banks._shared.generic_bank import GenericBankConfig, GenericRuleEngine

CONFIG = GenericBankConfig(
    bank_key="bank_of_baroda",
    bank_name="Bank of Baroda",
    file_prefix="bank_of_baroda",
    markers=["bank of baroda", "baroda", "bob", "barb0"],
    support_aliases=["bank of baroda", "bankofbaroda", "bob", "baroda"],
)

logger = logging.getLogger(__name__)


@dataclass
class RuleClassificationResult:
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class BankOfBarodaRuleEngine:
    def __init__(self, keywords_file: Optional[str] = None):
        self.generic_rule_engine = GenericRuleEngine(CONFIG, keywords_file=keywords_file)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def classify(self, transactions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        processed: List[Dict[str, Any]] = []
        unclassified: List[Dict[str, Any]] = []

        for txn in transactions:
            result = self._classify_single(txn)
            txn_copy = dict(txn)
            is_debit = bool(txn.get("debit"))
            txn_copy["category"] = normalize_category(result.category, is_debit=is_debit)
            txn_copy["confidence"] = result.confidence
            txn_copy["source"] = result.source
            txn_copy["matched_rule"] = result.matched_rule
            txn_copy["matched_keyword"] = result.matched_keyword
            processed.append(txn_copy)
            if txn_copy["category"].startswith("Others"):
                unclassified.append(txn_copy)

        return processed, unclassified

    def _classify_single(self, txn: Dict[str, Any]) -> RuleClassificationResult:
        description = str(txn.get("description") or "").upper()
        is_debit = bool(txn.get("debit"))

        exact_rules = [
            ("ATM/CASH/", "ATM Withdrawal", 0.99, "atm_cash"),
            ("CHARGES FOR", "Bank Charges", 0.99, "charges_for"),
            ("REVERSAL", "Refund", 0.95, "reversal"),
            ("NETFLIX", "Subscription", 0.95, "netflix"),
            ("MONTHLY TRANSFER", "Transfer", 0.95, "monthly_transfer"),
            ("INSTALLMENT", "Loan Payment", 0.95, "installment"),
            ("TVSCREDITSERVICESLTD", "Loan Payment", 0.95, "tvs_credit"),
            ("IDFC FIRST", "Loan Payment", 0.95, "idfc_first"),
            ("BY CASH", "Cash Deposit", 0.95, "by_cash"),
        ]
        for token, category, confidence, matched_rule in exact_rules:
            if token in description:
                return RuleClassificationResult(
                    category=category,
                    confidence=confidence,
                    source="rule_engine",
                    matched_rule=matched_rule,
                    matched_keyword=token,
                )

        if any(token in description for token in ("UPI/", "IMPS/P2A/", "MBK/")):
            category = "Transfer"
            if (not is_debit) and "BY CASH" in description:
                category = "Cash Deposit"
            return RuleClassificationResult(
                category=category,
                confidence=0.9,
                source="rule_engine",
                matched_rule="transfer_channel",
                matched_keyword="channel",
            )

        generic_classified, generic_unclassified = self.generic_rule_engine.classify([txn])
        if generic_classified and not generic_unclassified:
            fallback = generic_classified[0]
            return RuleClassificationResult(
                category=str(fallback.get("category") or ("Others Debit" if is_debit else "Others Credit")),
                confidence=float(fallback.get("confidence") or 0.85),
                source=str(fallback.get("source") or "generic_rule_engine"),
                matched_rule=fallback.get("matched_rule"),
                matched_keyword=fallback.get("matched_keyword"),
            )

        return RuleClassificationResult(
            category="Others Debit" if is_debit else "Others Credit",
            confidence=0.5,
            source="rule_engine",
            matched_rule="default",
        )
