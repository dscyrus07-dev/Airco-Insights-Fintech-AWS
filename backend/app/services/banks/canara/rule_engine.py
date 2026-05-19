"""
Airco Insights - Canara Bank Rule Engine
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.banks._shared.category_registry import normalize_category
from app.services.banks._shared.generic_bank import GenericBankConfig, GenericRuleEngine

CONFIG = GenericBankConfig(
    bank_key="canara",
    bank_name="Canara Bank",
    file_prefix="canara",
    markers=["canara bank", "current & saving account statement", "cnrb"],
    support_aliases=["canara", "canara bank"],
)

logger = logging.getLogger(__name__)


@dataclass
class RuleClassificationResult:
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class CanaraRuleEngine:
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
            ("GROSS INT CR", "Interest Income", 0.99, "gross_interest"),
            ("SBINT FOR THE PERIOD", "Interest Income", 0.99, "sb_interest"),
            ("GST REV", "Refund", 0.95, "gst_reversal"),
            ("UPI/CR/", "Transfer", 0.95, "upi_credit"),
            ("UPI/DR/", "Transfer", 0.95, "upi_debit"),
            ("IB OAT", "Transfer", 0.94, "ib_oat_transfer"),
            ("IB ITG", "Transfer", 0.94, "ib_itg_transfer"),
            ("NEFT CR-", "Transfer", 0.95, "neft_credit"),
            ("INET-IMPS-CR", "Transfer", 0.95, "imps_credit"),
            ("EFS. BY XFER. FROM CASA", "Transfer", 0.95, "efs_casa_transfer"),
            ("BY XFER. FROM CASA", "Transfer", 0.95, "casa_transfer"),
            ("ATM CASH", "ATM Withdrawal", 0.95, "atm_cash"),
            ("ATM INSUFFICIENT FUND CHARGES", "Bank Charges", 0.99, "atm_insufficient"),
            ("ATM / IMPS TRANSACTION CHARGE", "Bank Charges", 0.99, "atm_imps_charge"),
            ("ATM / IMPS TRANSACTION CHARGES", "Bank Charges", 0.99, "atm_imps_charges"),
            ("SMS CHARGES", "Bank Charges", 0.99, "sms_charge"),
            ("SLABWISE NMMB CHARGES", "Bank Charges", 0.99, "nmmb_charge"),
            ("ECS ", "Loan Payment", 0.92, "ecs_debit"),
            ("RD DRAWDOWN", "Investment", 0.9, "rd_drawdown"),
            ("INSTL PAY TO RD", "Investment", 0.9, "rd_installment"),
            ("FD REDEEM PRINCIPAL", "Investment Returns", 0.92, "fd_redeem_principal"),
            ("FD REDEEM INTEREST", "Interest Income", 0.92, "fd_redeem_interest"),
            ("CASHFREE PAYMENTS INDIA PRIVATE", "Business Income", 0.9, "cashfree"),
            ("-NALLURI", "Transfer", 0.9, "named_transfer"),
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
