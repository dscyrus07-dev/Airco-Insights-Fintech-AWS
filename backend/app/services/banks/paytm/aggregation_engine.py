"""
Airco Insights — Paytm Bank Aggregation Engine
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CategorySummary:
    category: str; total_amount: float; transaction_count: int; avg_amount: float; percentage: float


@dataclass
class MonthlySummary:
    month: str; total_credits: float; total_debits: float; net_flow: float
    transaction_count: int; credit_count: int; debit_count: int


@dataclass
class AggregationResult:
    opening_balance: float; closing_balance: float; total_credits: float; total_debits: float
    credit_count: int; debit_count: int; monthly_summary: Dict[str, Dict]
    debit_categories: List[CategorySummary] = field(default_factory=list)
    credit_categories: List[CategorySummary] = field(default_factory=list)
    monthly_summaries: List[MonthlySummary] = field(default_factory=list)
    weekly_credits: Dict[str, float] = field(default_factory=dict)
    weekly_debits: Dict[str, float] = field(default_factory=dict)
    recurring_total: float = 0.0; one_time_total: float = 0.0
    recurring_count: int = 0; one_time_count: int = 0
    top_debit_merchants: List[Dict[str, Any]] = field(default_factory=list)
    top_credit_merchants: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "opening_balance": self.opening_balance, "closing_balance": self.closing_balance,
            "total_credits": self.total_credits, "total_debits": self.total_debits,
            "credit_count": self.credit_count, "debit_count": self.debit_count,
            "debit_categories": [{"category":c.category,"total":c.total_amount,"count":c.transaction_count,
                                   "avg":c.avg_amount,"percentage":c.percentage} for c in self.debit_categories],
            "credit_categories": [{"category":c.category,"total":c.total_amount,"count":c.transaction_count,
                                    "avg":c.avg_amount,"percentage":c.percentage} for c in self.credit_categories],
            "monthly": [{"month":m.month,"credits":m.total_credits,"debits":m.total_debits,
                         "net":m.net_flow,"count":m.transaction_count} for m in self.monthly_summaries],
            "weekly_credits": self.weekly_credits, "weekly_debits": self.weekly_debits,
            "recurring": {"total":self.recurring_total,"count":self.recurring_count},
            "one_time": {"total":self.one_time_total,"count":self.one_time_count},
        }


class PaytmAggregationEngine:
    TOP_MERCHANTS_LIMIT = 10

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def aggregate(self, transactions: List[Dict[str, Any]],
                  opening: Optional[float] = None, closing: Optional[float] = None) -> AggregationResult:
        if not transactions:
            return AggregationResult(opening_balance=opening or 0, closing_balance=closing or 0,
                                     total_credits=0, total_debits=0, credit_count=0, debit_count=0, monthly_summary={})
        self.logger.info("Aggregating %d Paytm transactions", len(transactions))
        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits  = sum(t.get("debit")  or 0 for t in transactions)
        credit_count  = sum(1 for t in transactions if (t.get("credit") or 0) > 0)
        debit_count   = sum(1 for t in transactions if (t.get("debit")  or 0) > 0)
        debit_cats    = self._agg_categories(transactions, True)
        credit_cats   = self._agg_categories(transactions, False)
        monthly_sums  = self._agg_monthly(transactions)
        monthly_summary = {m.month: {"credits":m.total_credits,"debits":m.total_debits,
                                      "credit_count":m.credit_count,"debit_count":m.debit_count}
                           for m in monthly_sums}
        wc, wd = self._agg_weekly(transactions)
        rs     = self._agg_recurring(transactions)
        return AggregationResult(
            opening_balance=opening or 0,
            closing_balance=closing or (transactions[-1].get("balance") or 0),
            total_credits=total_credits, total_debits=total_debits,
            credit_count=credit_count, debit_count=debit_count,
            monthly_summary=monthly_summary, debit_categories=debit_cats, credit_categories=credit_cats,
            monthly_summaries=monthly_sums, weekly_credits=wc, weekly_debits=wd,
            recurring_total=rs["recurring_total"], one_time_total=rs["one_time_total"],
            recurring_count=rs["recurring_count"], one_time_count=rs["one_time_count"],
            top_debit_merchants=self._top_merchants(transactions, True),
            top_credit_merchants=self._top_merchants(transactions, False),
        )

    def _agg_categories(self, transactions, is_debit):
        data: Dict[str, Dict] = defaultdict(lambda: {"total":0.0,"count":0})
        for t in transactions:
            if is_debit and t.get("debit"):
                data[t.get("category","Others Debit")]["total"]+=t["debit"]; data[t.get("category","Others Debit")]["count"]+=1
            elif not is_debit and t.get("credit"):
                data[t.get("category","Others Credit")]["total"]+=t["credit"]; data[t.get("category","Others Credit")]["count"]+=1
        grand=sum(d["total"] for d in data.values())
        sums=[CategorySummary(cat,round(d["total"],2),d["count"],
                              round(d["total"]/d["count"],2) if d["count"] else 0,
                              round(d["total"]/grand*100,1) if grand else 0) for cat,d in data.items()]
        sums.sort(key=lambda x: x.total_amount, reverse=True)
        return sums

    def _agg_monthly(self, transactions):
        data: Dict[str, Dict] = defaultdict(lambda: {"credits":0.0,"debits":0.0,"count":0,"cc":0,"dc":0})
        for t in transactions:
            ds=t.get("date","")
            if not ds: continue
            try: mk=str(ds)[:7] if "-" in str(ds) else f"20{str(ds).split('/')[2]}-{str(ds).split('/')[1]}"
            except (IndexError,ValueError): continue
            c=t.get("credit") or 0; d=t.get("debit") or 0
            data[mk]["credits"]+=c; data[mk]["debits"]+=d; data[mk]["count"]+=1
            if c>0: data[mk]["cc"]+=1
            if d>0: data[mk]["dc"]+=1
        return [MonthlySummary(k,round(v["credits"],2),round(v["debits"],2),
                               round(v["credits"]-v["debits"],2),v["count"],v["cc"],v["dc"])
                for k,v in sorted(data.items())]

    def _agg_weekly(self, transactions):
        wc: Dict[str,float]=defaultdict(float); wd: Dict[str,float]=defaultdict(float)
        for t in transactions:
            ds=t.get("date","")
            if not ds: continue
            try:
                dt=datetime.strptime(str(ds)[:10],"%Y-%m-%d"); y,w,_=dt.isocalendar(); wk=f"{y}-W{w:02d}"
            except ValueError: continue
            wc[wk]+=t.get("credit") or 0; wd[wk]+=t.get("debit") or 0
        return dict(wc), dict(wd)

    def _agg_recurring(self, transactions):
        rt=ot=0.0; rc=oc=0
        for t in transactions:
            amt=(t.get("debit") or 0)+(t.get("credit") or 0)
            if t.get("is_recurring"): rt+=amt; rc+=1
            else: ot+=amt; oc+=1
        return {"recurring_total":round(rt,2),"one_time_total":round(ot,2),"recurring_count":rc,"one_time_count":oc}

    def _top_merchants(self, transactions, is_debit):
        data: Dict[str,Dict]=defaultdict(lambda: {"total":0.0,"count":0})
        for t in transactions:
            amt=t.get("debit") if is_debit else t.get("credit")
            if not amt: continue
            m=str(t.get("description","Unknown"))[:30].strip()
            data[m]["total"]+=amt; data[m]["count"]+=1
        return [{"merchant":m,"total":round(v["total"],2),"count":v["count"]}
                for m,v in sorted(data.items(),key=lambda x:x[1]["total"],reverse=True)[:self.TOP_MERCHANTS_LIMIT]]
