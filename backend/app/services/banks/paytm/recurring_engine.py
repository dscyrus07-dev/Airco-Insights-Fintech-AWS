"""
Airco Insights — Paytm Bank Recurring Engine
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
    merchant_key: str; transaction_count: int; avg_amount: float; frequency: str; recurring_type: str


class PaytmRecurringEngine:
    SUBSCRIPTION_MERCHANTS = {
        "netflix","hotstar","prime","spotify","apple","youtube","gaana","wynk","jiosaavn",
        "zee5","sonyliv","discovery","linkedin","microsoft","google","adobe","dropbox",
    }
    EMI_PATTERNS     = [r"EMI.*\d+/\d+", r"LOAN.*EMI", r".*EMI.*DEBIT", r"ECS.*DR", r"NACH.*DR"]
    UTILITY_PATTERNS = [r"ELECTRICITY",r"POWER",r"GAS",r"WATER",r"BROADBAND",r"DTH",r"INSURANCE.*PREMIUM"]
    SALARY_PATTERNS  = [r"SALARY",r"SAL\s*CR",r"PAYROLL",r"WAGES"]
    WEEKLY_RANGE=(5,9); MONTHLY_RANGE=(25,35); QUARTERLY_RANGE=(85,95); AMOUNT_TOLERANCE=0.05

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._emi     = [re.compile(p, re.IGNORECASE) for p in self.EMI_PATTERNS]
        self._utility = [re.compile(p, re.IGNORECASE) for p in self.UTILITY_PATTERNS]
        self._salary  = [re.compile(p, re.IGNORECASE) for p in self.SALARY_PATTERNS]

    def detect(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        groups = self._group_by_merchant(transactions)
        patterns = self._detect_patterns(groups)
        result = []
        for txn in transactions:
            t = dict(txn); mk = self._merchant_key(txn); known = self._known_pattern(txn)
            if known:
                t["is_recurring"]=True; t["recurring_type"]=known[0]; t["recurring_frequency"]=known[1]
            elif mk in patterns:
                p=patterns[mk]; t["is_recurring"]=True; t["recurring_type"]=p.recurring_type; t["recurring_frequency"]=p.frequency
            else:
                t["is_recurring"]=False; t["recurring_type"]=None; t["recurring_frequency"]=None
            t["recurring"]="Yes" if t["is_recurring"] else "No"
            result.append(t)
        self.logger.info("Paytm recurring detected: %d", sum(1 for t in result if t.get("is_recurring")))
        return result

    def _group_by_merchant(self, txns):
        g = defaultdict(list)
        for t in txns:
            k = self._merchant_key(t)
            if k: g[k].append(t)
        return dict(g)

    def _merchant_key(self, txn):
        desc = (txn.get("description") or "").upper()
        for pfx in ("UPI-","NEFT-","IMPS-","POS "):
            if desc.startswith(pfx): desc = desc[len(pfx):]
        words = [w for w in re.findall(r"[A-Z]+", desc) if len(w)>2]
        return "_".join(words[:2]).lower() if words else ""

    def _detect_patterns(self, groups):
        patterns = {}
        for key, txns in groups.items():
            if len(txns)<2: continue
            sorted_t = sorted(txns, key=lambda t: t.get("date",""))
            intervals = []
            for i in range(1, len(sorted_t)):
                try:
                    d0=datetime.strptime(sorted_t[i-1]["date"],"%Y-%m-%d"); d1=datetime.strptime(sorted_t[i]["date"],"%Y-%m-%d")
                    delta=(d1-d0).days
                    if delta>0: intervals.append(delta)
                except (ValueError,KeyError): continue
            if not intervals: continue
            avg=sum(intervals)/len(intervals)
            freq=(("weekly" if self.WEEKLY_RANGE[0]<=avg<=self.WEEKLY_RANGE[1] else None) or
                  ("monthly" if self.MONTHLY_RANGE[0]<=avg<=self.MONTHLY_RANGE[1] else None) or
                  ("quarterly" if self.QUARTERLY_RANGE[0]<=avg<=self.QUARTERLY_RANGE[1] else None))
            if not freq: continue
            amounts=[t.get("debit") or t.get("credit") or 0 for t in txns]
            avg_amt=sum(amounts)/len(amounts)
            if avg_amt and not all(abs(a-avg_amt)/avg_amt<=self.AMOUNT_TOLERANCE for a in amounts): continue
            patterns[key]=RecurringPattern(key,len(txns),avg_amt,freq,self._type(key,txns))
        return patterns

    def _type(self, key, txns):
        if key in self.SUBSCRIPTION_MERCHANTS: return "subscription"
        desc=(txns[0].get("description") or "").upper()
        for p in self._emi:
            if p.search(desc): return "emi"
        for p in self._utility:
            if p.search(desc): return "utility"
        for p in self._salary:
            if p.search(desc): return "salary"
        return "recurring"

    def _known_pattern(self, txn) -> Optional[Tuple[str,str]]:
        desc=(txn.get("description") or "").upper()
        for p in self._emi:
            if p.search(desc): return ("emi","monthly")
        if txn.get("credit"):
            for p in self._salary:
                if p.search(desc): return ("salary","monthly")
        for m in self.SUBSCRIPTION_MERCHANTS:
            if m in desc.lower(): return ("subscription","monthly")
        for p in self._utility:
            if p.search(desc): return ("utility","monthly")
        return None
