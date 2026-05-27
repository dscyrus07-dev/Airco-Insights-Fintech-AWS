"""
Airco Insights — Canara Bank Rule Engine
==========================================
Deterministic classification engine for Canara Bank transactions.
Mirrors HDFCRuleEngine: exact keywords, regex patterns, UPI detection,
amount-range heuristics, and get_statistics().
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.banks._shared.generic_bank import GenericBankConfig

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
    """Full-grade deterministic rule engine for Canara Bank transactions."""

    CONF_EXACT   = 0.99
    CONF_PATTERN = 0.95
    CONF_UPI     = 0.85
    CONF_AMOUNT  = 0.70

    DEBIT_RULES: Dict[str, Dict] = {
        "ATM Withdrawal": {
            "exact": ["ATM CASH", "ATM WDL", "ATW", "CASH WITHDRAWAL", "CASH W/D"],
            "patterns": [r"ATM.*CASH", r"ATW-\d+", r"CASH\s*W/D"],
        },
        "Bank Charges": {
            "exact": [
                "SMS CHARGES", "SLABWISE NMMB CHARGES", "ATM INSUFFICIENT FUND CHARGES",
                "ATM / IMPS TRANSACTION CHARGE", "ATM / IMPS TRANSACTION CHARGES",
                "MAINTENANCE CHARGE", "ANNUAL CHARGES", "LEDGER FOLIO CHARGES",
                "MINIMUM BALANCE CHARGE", "MIN BAL CHARGE", "DEBIT CARD ANNUAL FEE",
                "GST ON CHARGES",
            ],
            "patterns": [r".*CHARGES.*", r".*CHARGE.*FEE.*", r".*ANNUAL.*FEE.*"],
        },
        "Loan Payments": {
            "exact": ["EMI", "ECS ", "NACH DR", "LOAN EMI", "LOAN REPAY", "SI DEBIT", "STANDING INST"],
            "patterns": [r"ECS.*DR", r"NACH.*DR", r".*EMI.*\d+", r"LOAN.*REPAY"],
        },
        "Food": {
            "exact": ["SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "KFC", "PIZZA", "RESTAURANT", "FOOD"],
            "patterns": [r"SWIGGY.*", r"ZOMATO.*ORDER"],
        },
        "Shopping": {
            "exact": ["AMAZON", "FLIPKART", "MYNTRA", "MEESHO", "NYKAA", "AJIO", "BIGBASKET", "BLINKIT", "ZEPTO"],
            "patterns": [r"AMZN.*MKTP", r"FLIPKART.*INTERNET"],
        },
        "Transport": {
            "exact": ["UBER", "OLA", "RAPIDO", "PETROL", "DIESEL", "FUEL", "FASTAG", "IRCTC", "REDBUS", "MAKEMYTRIP"],
            "patterns": [r"UBER.*TRIP", r"OLA.*CAB", r"FASTAG.*", r"IRCTC.*"],
        },
        "Bill Payment": {
            "exact": [
                "ELECTRICITY", "WATER BILL", "GAS BILL", "BROADBAND", "MOBILE RECHARGE",
                "AIRTEL", "JIO", "BSNL", "VI ", "TATA SKY", "DISH TV",
            ],
            "patterns": [r".*RECHARGE.*", r"BILL.*PAYMENT", r"MOBILE.*BILL"],
        },
        "Entertainment": {
            "exact": ["NETFLIX", "HOTSTAR", "AMAZON PRIME", "SPOTIFY", "ZEE5", "SONYLIV", "YOUTUBE PREMIUM"],
            "patterns": [r"NETFLIX.*", r"PRIME.*MEMBER"],
        },
        "Insurance": {
            "exact": ["LIC PREMIUM", "INSURANCE PREMIUM", "LIC ", "HDFC LIFE", "SBI LIFE", "ICICI PRU"],
            "patterns": [r".*INSURANCE.*PREMIUM.*", r"LIC.*PREMIUM"],
        },
        "Investment": {
            "exact": ["RD DRAWDOWN", "INSTL PAY TO RD", "MUTUAL FUND", "SIP", "NSC", "PPF"],
            "patterns": [r"RD.*DRAWDOWN", r".*SIP.*", r"MUTUAL.*FUND"],
        },
        "Education": {
            "exact": ["SCHOOL FEES", "COLLEGE FEES", "TUITION", "BYJU", "UNACADEMY"],
            "patterns": [r"SCHOOL.*FEE", r"COLLEGE.*FEE"],
        },
        "Health": {
            "exact": ["PHARMACY", "HOSPITAL", "CLINIC", "DOCTOR", "MEDICAL", "APOLLO", "MEDPLUS"],
            "patterns": [r".*PHARMACY.*", r".*HOSPITAL.*"],
        },
        "Transfer": {
            "exact": [
                "NEFT DR", "RTGS DR", "IMPS DR", "IB OAT", "IB ITG",
                "BY XFER", "EFS. BY XFER", "SELF TRANSFER",
            ],
            "patterns": [r"NEFT.*DR", r"RTGS.*DR", r"IMPS.*DR", r"UPI.*DR"],
        },
    }

    CREDIT_RULES: Dict[str, Dict] = {
        "Salary": {
            "exact": ["SALARY", "SAL CR", "PAYROLL", "WAGES", "SALARY CREDIT"],
            "patterns": [r"SAL.*CR", r"PAYROLL.*CR", r"SALARY.*CREDIT"],
        },
        "Interest Income": {
            "exact": [
                "GROSS INT CR", "SBINT FOR THE PERIOD", "INT CR", "INTEREST CREDIT",
                "FD REDEEM INTEREST", "SB INTEREST",
            ],
            "patterns": [r"INT.*CR", r"INTEREST.*CR", r"FD.*INTEREST"],
        },
        "Investment Returns": {
            "exact": ["FD REDEEM PRINCIPAL", "RD MATURITY", "MF REDEMPTION"],
            "patterns": [r"FD.*REDEEM", r"RD.*MATURITY"],
        },
        "Refund": {
            "exact": ["REFUND", "REVERSAL", "CASHBACK", "CASH BACK", "GST REV"],
            "patterns": [r".*REFUND.*", r".*REVERSAL.*", r"GST.*REV"],
        },
        "Loan Credit": {
            "exact": ["LOAN DISBURSAL", "LOAN CREDIT", "DISBURSEMENT"],
            "patterns": [r"LOAN.*DISBURSAL", r"LOAN.*CR"],
        },
        "Business Income": {
            "exact": ["CASHFREE PAYMENTS INDIA PRIVATE", "RAZORPAY", "PAYTM PAYMENTS"],
            "patterns": [r"CASHFREE.*", r"RAZORPAY.*CR"],
        },
        "Transfer": {
            "exact": [
                "NEFT CR", "RTGS CR", "IMPS CR", "IB OAT", "IB ITG",
                "INET-IMPS-CR", "EFS. BY XFER. FROM CASA", "BY XFER. FROM CASA",
            ],
            "patterns": [r"NEFT.*CR", r"RTGS.*CR", r"IMPS.*CR", r"UPI.*CR"],
        },
    }

    UPI_MERCHANTS: Dict[str, str] = {
        "swiggy": "Food", "zomato": "Food",
        "amazon": "Shopping", "flipkart": "Shopping",
        "uber": "Transport", "ola": "Transport",
        "netflix": "Entertainment", "hotstar": "Entertainment",
    }

    def __init__(self, keywords_file: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self._debit_compiled: Dict[str, Dict] = {}
        for cat, rules in self.DEBIT_RULES.items():
            self._debit_compiled[cat] = {
                "exact": set(k.upper() for k in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }
        self._credit_compiled: Dict[str, Dict] = {}
        for cat, rules in self.CREDIT_RULES.items():
            self._credit_compiled[cat] = {
                "exact": set(k.upper() for k in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }

    def classify(
        self, transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        classified, unclassified = [], []
        for txn in transactions:
            result = self._classify_single(txn)
            txn_copy = dict(txn)
            txn_copy["category"] = result.category
            txn_copy["confidence"] = result.confidence
            txn_copy["source"] = result.source
            txn_copy["matched_rule"] = result.matched_rule
            (unclassified if result.category.startswith("Others") else classified).append(txn_copy)
        self.logger.info("Canara classify: %d ok, %d unclassified", len(classified), len(unclassified))
        return classified + unclassified, unclassified

    def _classify_single(self, txn: Dict[str, Any]) -> RuleClassificationResult:
        desc = str(txn.get("description") or "").upper()
        is_debit = bool(txn.get("debit"))
        rules = self._debit_compiled if is_debit else self._credit_compiled
        default = "Others Debit" if is_debit else "Others Credit"

        for cat, compiled in rules.items():
            for kw in compiled["exact"]:
                if kw in desc:
                    return RuleClassificationResult(cat, self.CONF_EXACT, "rule_engine", "exact_keyword", kw)

        for cat, compiled in rules.items():
            for pat in compiled["patterns"]:
                if pat.search(desc):
                    return RuleClassificationResult(cat, self.CONF_PATTERN, "rule_engine", "pattern_match", pat.pattern)

        if is_debit:
            upi = self._classify_upi(desc)
            if upi:
                return upi

        amount_res = self._classify_by_amount(txn.get("debit") or txn.get("credit") or 0, is_debit, desc)
        if amount_res:
            return amount_res

        return RuleClassificationResult(default, 0.5, "rule_engine", "default")

    def _classify_upi(self, description: str) -> Optional[RuleClassificationResult]:
        if "UPI" not in description and "@" not in description:
            return None
        desc_lower = description.lower()
        for merchant, category in self.UPI_MERCHANTS.items():
            if merchant in desc_lower:
                return RuleClassificationResult(category, self.CONF_UPI, "rule_engine", "upi_merchant", merchant)
        return None

    def _classify_by_amount(self, amount: float, is_debit: bool, description: str) -> Optional[RuleClassificationResult]:
        if is_debit and amount > 0:
            if amount % 100 == 0 and 500 <= amount <= 50000:
                if any(k in description for k in ("ATM", "ATW", "CASH")):
                    return RuleClassificationResult("ATM Withdrawal", self.CONF_AMOUNT, "rule_engine", "amount_atm")
        if is_debit and 99 <= amount <= 999:
            if any(k in description for k in ("SUB", "MEMBERSHIP", "PREMIUM")):
                return RuleClassificationResult("Entertainment", self.CONF_AMOUNT, "rule_engine", "amount_subscription")
        return None

    def get_statistics(self) -> Dict[str, Any]:
        dr = sum(len(r["exact"]) + len(r["patterns"]) for r in self._debit_compiled.values())
        cr = sum(len(r["exact"]) + len(r["patterns"]) for r in self._credit_compiled.values())
        return {
            "debit_categories": len(self._debit_compiled),
            "credit_categories": len(self._credit_compiled),
            "debit_rules": dr,
            "credit_rules": cr,
            "upi_merchants": len(self.UPI_MERCHANTS),
            "total_rules": dr + cr,
        }
