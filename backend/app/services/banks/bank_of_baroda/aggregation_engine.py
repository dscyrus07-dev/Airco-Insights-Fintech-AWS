"""
Airco Insights - Bank of Baroda Aggregation Engine
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.services.banks._shared.generic_bank import GenericAggregationEngine, GenericBankConfig

CONFIG = GenericBankConfig(
    bank_key="bank_of_baroda",
    bank_name="Bank of Baroda",
    file_prefix="bank_of_baroda",
    markers=["bank of baroda", "baroda", "bob", "barb0"],
    support_aliases=["bank of baroda", "bankofbaroda", "bob", "baroda"],
)

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    credit_count: int
    debit_count: int
    monthly_summary: Dict[str, Dict]


class BankOfBarodaAggregationEngine(GenericAggregationEngine):
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def aggregate(self, transactions: List[Dict], opening: Optional[float] = None, closing: Optional[float] = None) -> AggregationResult:
        if not transactions:
            return AggregationResult(
                opening_balance=opening or 0,
                closing_balance=closing or 0,
                total_credits=0,
                total_debits=0,
                credit_count=0,
                debit_count=0,
                monthly_summary={},
            )

        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits = sum(t.get("debit") or 0 for t in transactions)
        credit_count = sum(1 for t in transactions if (t.get("credit") or 0) > 0)
        debit_count = sum(1 for t in transactions if (t.get("debit") or 0) > 0)

        # Monthly aggregation
        monthly_summary = self._aggregate_monthly(transactions)

        return AggregationResult(
            opening_balance=opening or 0,
            closing_balance=closing or transactions[-1].get("balance", 0),
            total_credits=total_credits,
            total_debits=total_debits,
            credit_count=credit_count,
            debit_count=debit_count,
            monthly_summary=monthly_summary,
        )

    def _aggregate_monthly(self, transactions: List[Dict]) -> Dict[str, Dict]:
        monthly = {}
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str:
                continue

            try:
                if isinstance(date_str, str):
                    if "-" in date_str:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(date_str, "%d/%m/%Y")
                else:
                    dt = date_str

                month_key = dt.strftime("%b-%Y")
                if month_key not in monthly:
                    monthly[month_key] = {
                        "credits": 0,
                        "debits": 0,
                        "credit_count": 0,
                        "debit_count": 0,
                    }

                credit = txn.get("credit") or 0
                debit = txn.get("debit") or 0

                if credit > 0:
                    monthly[month_key]["credits"] += credit
                    monthly[month_key]["credit_count"] += 1
                if debit > 0:
                    monthly[month_key]["debits"] += debit
                    monthly[month_key]["debit_count"] += 1
            except Exception:
                continue

        return monthly
