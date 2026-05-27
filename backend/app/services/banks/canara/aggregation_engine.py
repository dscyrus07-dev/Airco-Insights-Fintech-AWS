"""
Airco Insights — Canara Bank Aggregation Engine
================================================
Full-grade analytics mirroring HDFCAggregationEngine:
category breakdown, monthly + weekly summaries,
recurring vs one-time split, top-10 merchants.
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
    category: str
    total_amount: float
    transaction_count: int
    avg_amount: float
    percentage: float


@dataclass
class MonthlySummary:
    month: str
    total_credits: float
    total_debits: float
    net_flow: float
    transaction_count: int
    credit_count: int
    debit_count: int


@dataclass
class AggregationResult:
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    credit_count: int
    debit_count: int
    monthly_summary: Dict[str, Dict]
    # Extended HDFC-grade fields
    debit_categories: List[CategorySummary] = field(default_factory=list)
    credit_categories: List[CategorySummary] = field(default_factory=list)
    monthly_summaries: List[MonthlySummary] = field(default_factory=list)
    weekly_credits: Dict[str, float] = field(default_factory=dict)
    weekly_debits: Dict[str, float] = field(default_factory=dict)
    recurring_total: float = 0.0
    one_time_total: float = 0.0
    recurring_count: int = 0
    one_time_count: int = 0
    top_debit_merchants: List[Dict[str, Any]] = field(default_factory=list)
    top_credit_merchants: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_credits": self.total_credits,
            "total_debits": self.total_debits,
            "credit_count": self.credit_count,
            "debit_count": self.debit_count,
            "debit_categories": [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount,
                 "percentage": c.percentage}
                for c in self.debit_categories
            ],
            "credit_categories": [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount,
                 "percentage": c.percentage}
                for c in self.credit_categories
            ],
            "monthly": [
                {"month": m.month, "credits": m.total_credits, "debits": m.total_debits,
                 "net": m.net_flow, "count": m.transaction_count}
                for m in self.monthly_summaries
            ],
            "weekly_credits": self.weekly_credits,
            "weekly_debits": self.weekly_debits,
            "recurring": {"total": self.recurring_total, "count": self.recurring_count},
            "one_time": {"total": self.one_time_total, "count": self.one_time_count},
        }


class CanaraAggregationEngine:
    """Full-grade aggregation engine for Canara Bank transactions."""

    TOP_MERCHANTS_LIMIT = 10

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def aggregate(
        self,
        transactions: List[Dict[str, Any]],
        opening: Optional[float] = None,
        closing: Optional[float] = None,
    ) -> AggregationResult:
        if not transactions:
            return AggregationResult(
                opening_balance=opening or 0, closing_balance=closing or 0,
                total_credits=0, total_debits=0, credit_count=0, debit_count=0,
                monthly_summary={},
            )

        self.logger.info("Aggregating %d Canara transactions", len(transactions))

        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits  = sum(t.get("debit")  or 0 for t in transactions)
        credit_count  = sum(1 for t in transactions if (t.get("credit") or 0) > 0)
        debit_count   = sum(1 for t in transactions if (t.get("debit")  or 0) > 0)

        debit_cats  = self._aggregate_categories(transactions, is_debit=True)
        credit_cats = self._aggregate_categories(transactions, is_debit=False)
        monthly_summaries = self._aggregate_monthly(transactions)
        monthly_summary   = {m.month: {"credits": m.total_credits, "debits": m.total_debits,
                                        "credit_count": m.credit_count, "debit_count": m.debit_count}
                              for m in monthly_summaries}
        weekly_credits, weekly_debits = self._aggregate_weekly(transactions)
        recurring_stats = self._aggregate_recurring(transactions)
        top_debit  = self._get_top_merchants(transactions, is_debit=True)
        top_credit = self._get_top_merchants(transactions, is_debit=False)

        return AggregationResult(
            opening_balance=opening or 0,
            closing_balance=closing or (transactions[-1].get("balance") or 0),
            total_credits=total_credits,
            total_debits=total_debits,
            credit_count=credit_count,
            debit_count=debit_count,
            monthly_summary=monthly_summary,
            debit_categories=debit_cats,
            credit_categories=credit_cats,
            monthly_summaries=monthly_summaries,
            weekly_credits=weekly_credits,
            weekly_debits=weekly_debits,
            recurring_total=recurring_stats["recurring_total"],
            one_time_total=recurring_stats["one_time_total"],
            recurring_count=recurring_stats["recurring_count"],
            one_time_count=recurring_stats["one_time_count"],
            top_debit_merchants=top_debit,
            top_credit_merchants=top_credit,
        )

    def _aggregate_categories(self, transactions: List[Dict], is_debit: bool) -> List[CategorySummary]:
        data: Dict[str, Dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
        for txn in transactions:
            if is_debit and txn.get("debit"):
                cat = txn.get("category", "Others Debit")
                data[cat]["total"] += txn["debit"]
                data[cat]["count"] += 1
            elif not is_debit and txn.get("credit"):
                cat = txn.get("category", "Others Credit")
                data[cat]["total"] += txn["credit"]
                data[cat]["count"] += 1
        grand = sum(d["total"] for d in data.values())
        summaries = []
        for cat, d in data.items():
            avg = d["total"] / d["count"] if d["count"] else 0
            pct = (d["total"] / grand * 100) if grand else 0
            summaries.append(CategorySummary(cat, round(d["total"], 2), d["count"], round(avg, 2), round(pct, 1)))
        summaries.sort(key=lambda x: x.total_amount, reverse=True)
        return summaries

    def _aggregate_monthly(self, transactions: List[Dict]) -> List[MonthlySummary]:
        data: Dict[str, Dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0, "cc": 0, "dc": 0})
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str:
                continue
            try:
                if "-" in str(date_str):
                    month_key = str(date_str)[:7]
                else:
                    parts = str(date_str).split("/")
                    year = parts[2] if len(parts[2]) == 4 else f"20{parts[2]}"
                    month_key = f"{year}-{parts[1]}"
            except (IndexError, ValueError):
                continue
            credit = txn.get("credit") or 0
            debit  = txn.get("debit")  or 0
            data[month_key]["credits"] += credit
            data[month_key]["debits"]  += debit
            data[month_key]["count"]   += 1
            if credit > 0: data[month_key]["cc"] += 1
            if debit  > 0: data[month_key]["dc"] += 1
        return [
            MonthlySummary(
                month=k,
                total_credits=round(v["credits"], 2),
                total_debits=round(v["debits"], 2),
                net_flow=round(v["credits"] - v["debits"], 2),
                transaction_count=v["count"],
                credit_count=v["cc"],
                debit_count=v["dc"],
            )
            for k, v in sorted(data.items())
        ]

    def _aggregate_weekly(self, transactions: List[Dict]) -> tuple:
        wc: Dict[str, float] = defaultdict(float)
        wd: Dict[str, float] = defaultdict(float)
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str:
                continue
            try:
                dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
                year, week, _ = dt.isocalendar()
                wk = f"{year}-W{week:02d}"
            except ValueError:
                continue
            wc[wk] += txn.get("credit") or 0
            wd[wk] += txn.get("debit")  or 0
        return dict(wc), dict(wd)

    def _aggregate_recurring(self, transactions: List[Dict]) -> Dict[str, Any]:
        rt, ot, rc, oc = 0.0, 0.0, 0, 0
        for txn in transactions:
            amt = (txn.get("debit") or 0) + (txn.get("credit") or 0)
            if txn.get("is_recurring"):
                rt += amt; rc += 1
            else:
                ot += amt; oc += 1
        return {"recurring_total": round(rt, 2), "one_time_total": round(ot, 2),
                "recurring_count": rc, "one_time_count": oc}

    def _get_top_merchants(self, transactions: List[Dict], is_debit: bool) -> List[Dict[str, Any]]:
        data: Dict[str, Dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
        for txn in transactions:
            amt = txn.get("debit") if is_debit else txn.get("credit")
            if not amt:
                continue
            merchant = str(txn.get("description", "Unknown"))[:30].strip()
            data[merchant]["total"] += amt
            data[merchant]["count"] += 1
        sorted_m = sorted(data.items(), key=lambda x: x[1]["total"], reverse=True)[:self.TOP_MERCHANTS_LIMIT]
        return [{"merchant": m, "total": round(v["total"], 2), "count": v["count"]} for m, v in sorted_m]
