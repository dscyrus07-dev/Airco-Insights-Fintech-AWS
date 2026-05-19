"""
Airco Insights - Paytm Bank Rule Engine
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.banks._shared.category_registry import normalize_category
from app.services.banks._shared.generic_bank import GenericBankConfig, GenericRuleEngine

CONFIG = GenericBankConfig(
    bank_key="paytm",
    bank_name="Paytm Bank",
    file_prefix="paytm",
    markers=["paytm payments bank", "account statement for:", "paytm"],
    support_aliases=["paytm", "paytm bank", "paytm payments bank"],
)

logger = logging.getLogger(__name__)


@dataclass
class RuleClassificationResult:
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class PaytmRuleEngine:
    def __init__(self, keywords_file: Optional[str] = None):
        self.keywords_file = keywords_file or self._resolve_keywords_file()
        self.generic_rule_engine = GenericRuleEngine(CONFIG, keywords_file=self.keywords_file)
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
            ("PAID USING YOUR BANK ACCOUNT", "Transfer", 0.98, "bank_to_wallet"),
            ("PAYTM ADD MONEY", "Transfer", 0.98, "paytm_add_money"),
            ("MONEY RECEIVED USING UPI", "Transfer", 0.94, "upi_receive"),
            ("MONEY SENT USING UPI", "Transfer", 0.94, "upi_send"),
            ("MONEY RECEIVED | RECEIVED FROM ONE97 COMMUNICATIONS LIMITED", "Business Income", 0.95, "one97_credit"),
            ("RESTORED AGAINST FAILED PAYMENT", "Refund", 0.99, "failed_payment_restore"),
            ("ADDED BACK TO SAVINGS ACCOUNT", "Refund", 0.96, "added_back"),
            ("NACH RETURN CHARGES", "Bank Charges", 0.99, "nach_return_charge"),
            ("DEDUCTED FOR AUTOMATIC PAYMENT", "Loan Payment", 0.97, "autopay_deduction"),
            ("PAID TO CTRAZORPAY", "Loan Payment", 0.96, "ctrazorpay_autopay"),
            ("PAYU FINANCE INDIA", "Loan Payment", 0.96, "payu_finance_autopay"),
            ("AMOUNT DEBITED", "Transfer", 0.84, "amount_debited"),
            ("CASHFREE PAYMENTS INDIA PRIVATE LIM", "Business Income", 0.95, "cashfree_credit"),
            ("WALLETMONEYTOBANK@PAYTM", "Transfer", 0.95, "wallet_to_bank"),
            ("BHARATPE", "Shopping", 0.9, "bharatpe"),
            ("AIRTEL", "Bill Payment", 0.92, "airtel"),
            ("PHONEPE", "Transfer", 0.88, "phonepe"),
            ("PAYTM", "Transfer", 0.82, "paytm_counterparty"),
        ]
        for token, category, confidence, matched_rule in exact_rules:
            if token in description:
                return RuleClassificationResult(category, confidence, "rule_engine", matched_rule, token)

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
            "Others Debit" if is_debit else "Others Credit",
            0.5,
            "rule_engine",
            "default",
        )

    def _resolve_keywords_file(self) -> Optional[str]:
        current = Path(__file__).resolve()
        repo_root = None
        for parent in current.parents:
            if parent.name == "backend":
                repo_root = parent.parent
                break
        if repo_root is None:
            repo_root = current.parents[-1]
        candidates = [
            repo_root / "banks" / "paytm" / "output" / "words.json",
            repo_root / "backend" / "words.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None
