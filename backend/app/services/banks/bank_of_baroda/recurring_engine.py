"""
Airco Insights — Bank of Baroda Recurring Engine
==================================================
Full-grade recurring detection mirroring HDFCRecurringEngine:
merchant grouping, weekly/monthly/quarterly frequency detection,
amount-consistency tolerance band, known-pattern matching.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RecurringPattern:
    merchant_key: str
    transaction_count: int
    avg_amount: float
    frequency: str
    recurring_type: str


class BankOfBarodaRecurringEngine:
    """Recurring transaction detection for Bank of Baroda."""

    SUBSCRIPTION_MERCHANTS = {
        "netflix", "hotstar", "prime", "spotify", "apple", "youtube",
        "gaana", "wynk", "jiosaavn", "zee5", "sonyliv", "discovery",
        "linkedin", "microsoft", "google", "adobe", "dropbox",
    }

    EMI_PATTERNS = [
        r"EMI.*\d+/\d+", r"LOAN.*EMI", r".*EMI.*DEBIT",
        r"BAJAJ\s*FIN", r"HOME\s*LOAN", r"CAR\s*LOAN",
        r"ECS.*DR", r"NACH.*DR",
    ]
    UTILITY_PATTERNS = [
        r"ELECTRICITY", r"POWER", r"GAS", r"WATER",
        r"BROADBAND", r"MOBILE.*RECHARGE", r"DTH", r"INSURANCE.*PREMIUM",
    ]
    SALARY_PATTERNS = [r"SALARY", r"SAL\s*CR", r"PAYROLL", r"WAGES"]

    WEEKLY_RANGE    = (5, 9)
    MONTHLY_RANGE   = (25, 35)
    QUARTERLY_RANGE = (85, 95)
    AMOUNT_TOLERANCE = 0.05

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._emi_compiled     = [re.compile(p, re.IGNORECASE) for p in self.EMI_PATTERNS]
        self._utility_compiled = [re.compile(p, re.IGNORECASE) for p in self.UTILITY_PATTERNS]
        self._salary_compiled  = [re.compile(p, re.IGNORECASE) for p in self.SALARY_PATTERNS]

    def detect(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.logger.info("Detecting recurring in %d BOB transactions", len(transactions))

        groups  = self._group_by_merchant(transactions)
        patterns = self._detect_patterns(groups)

        result = []
        for txn in transactions:
            txn_copy = dict(txn)
            mk  = self._get_merchant_key(txn)
            known = self._check_known_patterns(txn)
            if known:
                txn_copy["is_recurring"] = True
                txn_copy["recurring_type"] = known[0]
                txn_copy["recurring_frequency"] = known[1]
            elif mk in patterns:
                p = patterns[mk]
                txn_copy["is_recurring"] = True
                txn_copy["recurring_type"] = p.recurring_type
                txn_copy["recurring_frequency"] = p.frequency
            else:
                txn_copy["is_recurring"] = False
                txn_copy["recurring_type"] = None
                txn_copy["recurring_frequency"] = None
            txn_copy["recurring"] = "Yes" if txn_copy["is_recurring"] else "No"
            result.append(txn_copy)

        self.logger.info("Recurring detected: %d", sum(1 for t in result if t.get("is_recurring")))
        return result

    def _group_by_merchant(self, transactions: List[Dict]) -> Dict[str, List[Dict]]:
        groups: Dict[str, List[Dict]] = defaultdict(list)
        for txn in transactions:
            key = self._get_merchant_key(txn)
            if key:
                groups[key].append(txn)
        return dict(groups)

    def _get_merchant_key(self, txn: Dict) -> str:
        desc = (txn.get("description") or "").upper()
        for prefix in ("UPI-", "NEFT-", "IMPS-", "POS "):
            if desc.startswith(prefix):
                desc = desc[len(prefix):]
        words = [w for w in re.findall(r"[A-Z]+", desc) if len(w) > 2]
        return "_".join(words[:2]).lower() if words else ""

    def _detect_patterns(self, groups: Dict[str, List[Dict]]) -> Dict[str, RecurringPattern]:
        patterns = {}
        for key, txns in groups.items():
            if len(txns) < 2:
                continue
            sorted_txns = sorted(txns, key=lambda t: t.get("date", ""))
            intervals = self._calculate_intervals(sorted_txns)
            if not intervals:
                continue
            avg_interval = sum(intervals) / len(intervals)
            frequency = self._determine_frequency(avg_interval)
            if not frequency:
                continue
            amounts = [t.get("debit") or t.get("credit") or 0 for t in txns]
            avg_amt = sum(amounts) / len(amounts)
            if not self._check_amount_consistency(amounts, avg_amt):
                continue
            patterns[key] = RecurringPattern(
                merchant_key=key, transaction_count=len(txns),
                avg_amount=avg_amt, frequency=frequency,
                recurring_type=self._determine_type(key, txns),
            )
        return patterns

    def _calculate_intervals(self, sorted_txns: List[Dict]) -> List[int]:
        intervals = []
        for i in range(1, len(sorted_txns)):
            try:
                d0 = datetime.strptime(sorted_txns[i-1]["date"], "%Y-%m-%d")
                d1 = datetime.strptime(sorted_txns[i]["date"],   "%Y-%m-%d")
                delta = (d1 - d0).days
                if delta > 0:
                    intervals.append(delta)
            except (ValueError, KeyError):
                continue
        return intervals

    def _determine_frequency(self, avg_interval: float) -> Optional[str]:
        if self.WEEKLY_RANGE[0]    <= avg_interval <= self.WEEKLY_RANGE[1]:    return "weekly"
        if self.MONTHLY_RANGE[0]   <= avg_interval <= self.MONTHLY_RANGE[1]:   return "monthly"
        if self.QUARTERLY_RANGE[0] <= avg_interval <= self.QUARTERLY_RANGE[1]: return "quarterly"
        return None

    def _check_amount_consistency(self, amounts: List[float], avg: float) -> bool:
        if avg == 0:
            return False
        return all(abs(a - avg) / avg <= self.AMOUNT_TOLERANCE for a in amounts)

    def _determine_type(self, merchant_key: str, txns: List[Dict]) -> str:
        if merchant_key in self.SUBSCRIPTION_MERCHANTS:
            return "subscription"
        desc = (txns[0].get("description") or "").upper()
        for p in self._emi_compiled:
            if p.search(desc): return "emi"
        for p in self._utility_compiled:
            if p.search(desc): return "utility"
        for p in self._salary_compiled:
            if p.search(desc): return "salary"
        return "recurring"

    def _check_known_patterns(self, txn: Dict) -> Optional[Tuple[str, str]]:
        desc = (txn.get("description") or "").upper()
        for p in self._emi_compiled:
            if p.search(desc): return ("emi", "monthly")
        if txn.get("credit"):
            for p in self._salary_compiled:
                if p.search(desc): return ("salary", "monthly")
        desc_lower = desc.lower()
        for merchant in self.SUBSCRIPTION_MERCHANTS:
            if merchant in desc_lower: return ("subscription", "monthly")
        for p in self._utility_compiled:
            if p.search(desc): return ("utility", "monthly")
        return None
