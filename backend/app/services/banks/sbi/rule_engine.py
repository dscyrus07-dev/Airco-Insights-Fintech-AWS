"""
Airco Insights - SBI Bank Rule Engine
=====================================
Deterministic classification for SBI transactions with SBI-specific keywords
and a shared generic-bank fallback.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.banks._shared.generic_bank import GenericBankConfig, GenericRuleEngine

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class SBIRuleEngine:
    """SBI-specific deterministic rule engine."""

    BANK_KEYWORDS_FILE_CANDIDATES = [
        str(Path(__file__).resolve().parents[5] / "banks" / "sbi" / "output" / "words.json"),
        "/app/keywords.json",
        "/app/words.json",
        str(Path(__file__).resolve().parents[5] / "backend" / "words.json"),
        str(Path(__file__).resolve().parents[5] / "keywords.json"),
    ]

    CONF_EXACT = 0.99
    CONF_PATTERN = 0.95
    CONF_MERCHANT = 0.90
    CONF_UPI = 0.85
    CONF_AMOUNT = 0.70

    DEBIT_RULES = {
        "ATM Withdrawal": {
            "exact": ["ATM", "CASH WITHDRAWAL", "ATM CASH", "CDM"],
            "patterns": [r"ATM.*", r"CASH.*WITHDRA.*", r".*KOTHAWADA.*", r".*HANAMKONDA.*", r".*NALGONDA.*"],
        },
        "Food": {
            "exact": [
                "SWIGGY", "ZOMATO", "DOMINOS", "KFC", "MCDONALDS",
                "PIZZA", "SUBWAY", "STARBUCKS", "CAFE", "RESTAURANT",
                "HALDIRAM", "FAASOS", "REBEL FOODS", "BIRYANI",
                "BLINKIT COMMERC", "HYDERABAD IRANI", "NAGORI", "PUNJAB DHA",
            ],
            "patterns": [
                r"UPI.*SWIGGY.*", r"UPI.*ZOMATO.*", r"UPI.*BLINKIT.*", r"UPI.*CAFE.*",
            ],
        },
        "Shopping": {
            "exact": [
                "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "NYKAA",
                "DMART", "BIGBASKET", "ZEPTO", "JIOMART", "DECATHLON", "CROMA", "7 ELEVEN", "OTHPOS",
            ],
            "patterns": [r"UPI.*AMAZON.*", r"UPI.*FLIPKART.*", r"UPI.*7\s*ELEVEN.*", r"OTHPOS.*"],
        },
        "Transport": {
            "exact": [
                "UBER", "OLA", "RAPIDO", "PETROL", "DIESEL", "IRCTC", "METRO", "FASTAG",
                "TOLL", "REDBUS", "MAKEMYTRIP", "INDIGO",
            ],
            "patterns": [r"UPI.*RAPIDO.*", r"UPI.*UBER.*", r"UPI.*OLA.*", r"FASTAG.*"],
        },
        "Bill Payment": {
            "exact": [
                "ELECTRICITY", "BROADBAND", "RECHARGE", "AIRTEL", "JIO", "VI", "BSNL",
                "PHARMACY", "HOSPITAL", "GST", "CBDT", "TAX", "MAHARASHTRA SAL",
            ],
            "patterns": [
                r"BILL.*PAYMENT.*", r".*RECHARGE.*", r".*ELECTRICITY.*",
                r".*PHARMACY.*", r"UPI.*MAHARASHTRA.*SAL.*",
            ],
        },
        "Entertainment": {
            "exact": ["NETFLIX", "HOTSTAR", "AMAZON PRIME", "ZEE5", "SPOTIFY", "GOOGLE PLAY"],
            "patterns": [r"UPI.*NETFLIX.*", r"PRIME.*MEMBER.*"],
        },
        "Loan Payments": {
            "exact": [
                "EMI", "LOAN", "LIC HOUSING", "HOME LOAN", "BAJAJ FINANCE", "ACHDR",
                "MANDATE DEBIT", "CMP MANDATE DEBIT", "NORTHERN ARC", "TRUECREDIT", "MPOKKET",
                "CTRAZORPAY", "SHRIRAM AKARA CAPITAL", "NDX P2P PRIVATE LIM",
            ],
            "patterns": [r"NACH.*DEBIT.*", r"ECS.*DEBIT.*", r".*EMI.*", r"ACHDR.*", r"NACH.*", r".*MANDATE DEBIT.*"],
        },
        "Transfer": {
            "exact": ["NEFT", "RTGS", "IMPS", "UPI", "TRANSFER", "PHONEPE PRIVATE"],
            "patterns": [r"UPI/.*/.*/.*", r"NEFT.*", r"RTGS.*", r"IMPS.*", r".*SENT.*PAYT.*", r".*/PAYME.*", r".*/PAYMENT.*", r".*INB.*"],
        },
        "Cash Deposit": {
            "exact": ["CASH DEPOSIT", "CSH DEP", "CASH DEP", "DEPOSITED AT GCC"],
            "patterns": [r"CASH\s+DEPOSIT.*", r"CSH\s+DEP.*", r".*DEPOSITED AT GCC.*"],
        },
        "Insurance": {
            "exact": ["SHRIRAM LIFE", "LIFE INS", "INSURANCE", "SBIMF SIP"],
            "patterns": [r".*LIFE INS.*", r".*INSURANCE.*"],
        },
    }

    CREDIT_RULES = {
        "Salary Credits": {
            "exact": ["SALARY", "SAL", "PAYROLL", "WAGES"],
            "patterns": [r"SALARY.*", r"SAL.*CREDIT.*", r"PAYROLL.*"],
        },
        "Interest": {
            "exact": ["INTEREST", "INT", "CREDIT INTEREST"],
            "patterns": [r"INTEREST.*CREDIT.*", r".*INTEREST.*"],
        },
        "Refund": {
            "exact": ["REFUND", "REVERSAL", "CASHBACK"],
            "patterns": [r"REFUND.*", r".*REVERSAL.*", r".*CASHBACK.*"],
        },
        "Bank Transfer In": {
            "exact": ["NEFT CR", "RTGS CR", "IMPS CR", "PHONEPE PRIVATE", "PRIVATE FROM", "PRIVATE TO"],
            "patterns": [r"UPI/.*/.*/.*", r"NEFT.*CR.*", r"RTGS.*CR.*", r"IMPS.*CR.*", r".*RAMSUMAN.*", r".*INB.*", r".*/PAYME.*", r".*/PAYMENT.*", r"TRANSFER (?:TO|FROM).*"],
        },
        "Cash Deposit": {
            "exact": ["CASH DEPOSIT", "CSH DEP", "CASH DEP", "DEPOSITED AT GCC"],
            "patterns": [r"CASH\s+DEPOSIT.*", r"CSH\s+DEP.*", r".*DEPOSITED AT GCC.*"],
        },
    }

    UPI_MERCHANTS = {
        "swiggy": "Food",
        "zomato": "Food",
        "blinkit": "Food",
        "amazon": "Shopping",
        "flipkart": "Shopping",
        "rapido": "Transport",
        "uber": "Transport",
        "ola": "Transport",
        "netflix": "Entertainment",
        "hotstar": "Entertainment",
        "pharmeasy": "Bill Payment",
        "apollo": "Bill Payment",
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.generic_rule_engine = GenericRuleEngine(
            GenericBankConfig(
                bank_key="sbi",
                bank_name="SBI",
                file_prefix="sbi_report",
                markers=["STATE BANK OF INDIA", "SBI", "SBIN"],
            )
        )
        self._load_keywords_from_words_json()
        self._compile_patterns()

    def _load_keywords_from_words_json(self) -> None:
        for candidate in self.BANK_KEYWORDS_FILE_CANDIDATES:
            try:
                with open(candidate, "r", encoding="utf-8") as fh:
                    db = json.load(fh)
                self._refresh_rules_from_db(db)
                self.logger.info("Loaded SBI keyword database: %s", candidate)
                return
            except Exception:
                continue

    def _refresh_rules_from_db(self, db: Dict[str, Any]) -> None:
        classification = db.get("classification", {}) if isinstance(db, dict) else {}
        exact_targets = {
            "ATM Withdrawal": ["ATM_WITHDRAWAL"],
            "Food": ["FOOD_EXPENSE", "DINING"],
            "Shopping": ["SHOPPING", "GROCERIES"],
            "Transport": ["TRANSPORT", "FUEL", "TRAVEL"],
            "Bill Payment": ["BILL_PAYMENT", "UTILITIES", "MEDICAL"],
            "Entertainment": ["ENTERTAINMENT", "SUBSCRIPTION"],
            "Loan Payments": ["LOAN_PAYMENT", "EMI"],
            "Transfer": ["TRANSFER", "UPI_TRANSFER"],
            "Salary Credits": ["SALARY"],
            "Interest": ["INTEREST_INCOME"],
            "Refund": ["REFUND", "CASHBACK"],
            "Bank Transfer In": ["TRANSFER_IN", "BUSINESS_INCOME", "FREELANCE_INCOME"],
        }
        for target_category, source_keys in exact_targets.items():
            rule_set = self.DEBIT_RULES if target_category in self.DEBIT_RULES else self.CREDIT_RULES
            exact_values = set(rule_set[target_category]["exact"])
            for source_key in source_keys:
                source_group = classification.get(source_key, {})
                if isinstance(source_group, dict):
                    for values in source_group.values():
                        if isinstance(values, list):
                            exact_values.update(str(value).upper() for value in values if value)
                elif isinstance(source_group, list):
                    exact_values.update(str(value).upper() for value in source_group if value)
            rule_set[target_category]["exact"] = sorted(exact_values)

    def _compile_patterns(self) -> None:
        self._debit_compiled = {}
        self._credit_compiled = {}
        for category, rules in self.DEBIT_RULES.items():
            self._debit_compiled[category] = {
                "exact": set(keyword.upper() for keyword in rules.get("exact", [])),
                "patterns": [re.compile(pattern, re.IGNORECASE) for pattern in rules.get("patterns", [])],
            }
        for category, rules in self.CREDIT_RULES.items():
            self._credit_compiled[category] = {
                "exact": set(keyword.upper() for keyword in rules.get("exact", [])),
                "patterns": [re.compile(pattern, re.IGNORECASE) for pattern in rules.get("patterns", [])],
            }

    def classify(
        self,
        transactions: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        classified = []
        unclassified = []
        for txn in transactions:
            result = self._classify_single(txn)
            txn_copy = dict(txn)
            txn_copy["category"] = result.category
            txn_copy["confidence"] = result.confidence
            txn_copy["source"] = result.source
            txn_copy["matched_rule"] = result.matched_rule
            txn_copy["matched_keyword"] = result.matched_keyword
            if result.category.startswith("Others"):
                unclassified.append(txn_copy)
            else:
                classified.append(txn_copy)
        return classified, unclassified

    def _classify_single(self, txn: Dict[str, Any]) -> ClassificationResult:
        description = str(txn.get("description") or "").upper()
        is_debit = (txn.get("debit") or 0) > 0
        rules = self._debit_compiled if is_debit else self._credit_compiled
        default = "Others Debit" if is_debit else "Others Credit"

        for category, compiled in rules.items():
            for keyword in compiled["exact"]:
                if keyword in description:
                    return ClassificationResult(
                        category=category,
                        confidence=self.CONF_EXACT,
                        source="rule_engine",
                        matched_rule="exact_keyword",
                        matched_keyword=keyword,
                    )

        for category, compiled in rules.items():
            for pattern in compiled["patterns"]:
                if pattern.search(description):
                    return ClassificationResult(
                        category=category,
                        confidence=self.CONF_PATTERN,
                        source="rule_engine",
                        matched_rule="pattern_match",
                        matched_keyword=pattern.pattern,
                    )

        merchant_result = self._classify_merchant(description, is_debit)
        if merchant_result:
            return merchant_result

        upi_result = self._classify_upi_merchant(description)
        if upi_result:
            return upi_result

        amount_result = self._classify_amount(txn, is_debit)
        if amount_result:
            return amount_result

        generic_result = self._generic_fallback(txn)
        if generic_result:
            return generic_result

        return ClassificationResult(
            category=default,
            confidence=0.5,
            source="rule_engine",
            matched_rule="default",
        )

    def _classify_upi_merchant(self, description: str) -> Optional[ClassificationResult]:
        desc_lower = description.lower()
        for merchant, category in self.UPI_MERCHANTS.items():
            if merchant in desc_lower:
                return ClassificationResult(
                    category=category,
                    confidence=self.CONF_UPI,
                    source="rule_engine",
                    matched_rule="upi_merchant",
                    matched_keyword=merchant,
                )

        upi_match = re.match(r"UPI/([^/]+)/", description, re.IGNORECASE)
        if upi_match:
            merchant_name = upi_match.group(1).lower()
            for merchant, category in self.UPI_MERCHANTS.items():
                if merchant in merchant_name:
                    return ClassificationResult(
                        category=category,
                        confidence=self.CONF_UPI,
                        source="rule_engine",
                        matched_rule="upi_path_merchant",
                        matched_keyword=merchant,
                    )
        return None

    def _classify_merchant(self, description: str, is_debit: bool) -> Optional[ClassificationResult]:
        merchant_map = {
            "amazon": "Shopping" if is_debit else "Refund",
            "flipkart": "Shopping" if is_debit else "Refund",
            "myntra": "Shopping" if is_debit else "Refund",
            "ajio": "Shopping" if is_debit else "Refund",
            "nykaa": "Shopping" if is_debit else "Refund",
            "swiggy": "Food",
            "zomato": "Food",
            "dominos": "Food",
            "mcdonalds": "Food",
            "kfc": "Food",
            "uber": "Transport",
            "ola": "Transport",
            "rapido": "Transport",
            "netflix": "Entertainment",
            "hotstar": "Entertainment",
            "spotify": "Entertainment",
            "paytm": "Others Debit" if is_debit else "Transfer In",
            "phonepe": "Others Debit" if is_debit else "Transfer In",
            "gpay": "Others Debit" if is_debit else "Transfer In",
        }
        desc_lower = description.lower()
        for merchant, category in merchant_map.items():
            if merchant in desc_lower:
                return ClassificationResult(
                    category=category,
                    confidence=self.CONF_MERCHANT,
                    source="rule_engine",
                    matched_rule="merchant_mapping",
                    matched_keyword=merchant,
                )
        return None

    def _classify_amount(self, txn: Dict[str, Any], is_debit: bool) -> Optional[ClassificationResult]:
        amount = txn.get("debit") if is_debit else txn.get("credit")
        if not amount or amount <= 0:
            return None

        if is_debit and amount % 100 == 0 and 500 <= amount <= 100000:
            desc = str(txn.get("description") or "").lower()
            if any(keyword in desc for keyword in ["emi", "loan", "installment"]):
                return ClassificationResult(
                    category="Loan Payments",
                    confidence=self.CONF_AMOUNT,
                    source="rule_engine",
                    matched_rule="amount_emi",
                )

        if (not is_debit) and amount % 1000 == 0 and amount >= 10000:
            desc = str(txn.get("description") or "").lower()
            if any(keyword in desc for keyword in ["salary", "payroll", "wages"]):
                return ClassificationResult(
                    category="Salary Credits",
                    confidence=self.CONF_AMOUNT,
                    source="rule_engine",
                    matched_rule="amount_salary",
                )
        return None

    def _generic_fallback(self, txn: Dict[str, Any]) -> Optional[ClassificationResult]:
        try:
            classified, unclassified = self.generic_rule_engine.classify([txn])
        except Exception:
            self.logger.debug("Generic SBI fallback classification failed", exc_info=True)
            return None
        if not classified or unclassified:
            return None
        fallback = classified[0]
        category = str(fallback.get("category") or "").strip()
        if not category or category.startswith("Others"):
            return None
        return ClassificationResult(
            category=category,
            confidence=float(fallback.get("confidence") or self.CONF_MERCHANT),
            source="generic_rule_engine",
            matched_rule=fallback.get("matched_rule") or "generic_fallback",
            matched_keyword=fallback.get("matched_keyword"),
        )

    def get_statistics(self) -> Dict[str, Any]:
        debit_rules = sum(len(rules["exact"]) + len(rules["patterns"]) for rules in self._debit_compiled.values())
        credit_rules = sum(len(rules["exact"]) + len(rules["patterns"]) for rules in self._credit_compiled.values())
        return {"debit_rules": debit_rules, "credit_rules": credit_rules, "total_rules": debit_rules + credit_rules}
