"""
ICICI Bank report generator implementation.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ICICIReportGenerator(BaseBankReportGenerator):
    """ICICI Bank report generator."""

    def __init__(self):
        super().__init__("icici")

    async def generate_sheets(
        self,
        workbook: Workbook,
        transactions: List[Dict[str, Any]],
        user_info: Dict[str, Any],
        ai_results: Optional[Dict[str, Any]],
        options: Dict[str, Any],
    ) -> List[str]:
        sheets_created = []
        sheets_created.append(self._create_transactions_sheet(workbook, transactions))
        sheets_created.append(self._create_summary_sheet(workbook, transactions))
        sheets_created.append(self._create_category_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_icici_weekly_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_icici_bounce_penalty_sheet(workbook, transactions))
        sheets_created.append(self._create_icici_funds_received_sheet(workbook, transactions))
        sheets_created.append(self._create_icici_funds_remittance_sheet(workbook, transactions))

        for sheet_name in sheets_created:
            if sheet_name in workbook.sheetnames:
                self._apply_icici_styling(workbook[sheet_name])

        logger.info("ICICI report sheets generated", sheets=sheets_created)
        return sheets_created

    def _create_icici_weekly_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Weekly Analysis")
        headers = ["Week", "Credits", "Debits", "Net Flow", "Transactions"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

        weekly = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0})
        for txn in transactions:
            date = str(txn.get("date", ""))
            week = date[:7] if len(date) >= 7 else "Unknown"
            amount = float(txn.get("amount", 0) or 0)
            txn_type = str(txn.get("type", "")).lower()
            weekly[week]["count"] += 1
            if txn_type == "credit":
                weekly[week]["credits"] += amount
            else:
                weekly[week]["debits"] += amount

        for row, (week, data) in enumerate(sorted(weekly.items()), 2):
            ws.cell(row=row, column=1, value=week)
            ws.cell(row=row, column=2, value=data["credits"])
            ws.cell(row=row, column=3, value=data["debits"])
            ws.cell(row=row, column=4, value=data["credits"] - data["debits"])
            ws.cell(row=row, column=5, value=data["count"])

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

        return "Weekly Analysis"

    def _create_icici_bounce_penalty_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Bounces & Penal")
        headers = ["Metric", "Count", "Amount"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")

        bounce_count = 0
        penalty_count = 0
        bounce_amount = 0.0
        penalty_amount = 0.0
        for txn in transactions:
            desc = str(txn.get("description", "")).lower()
            amount = float(txn.get("amount", 0) or 0)
            if any(token in desc for token in ["bounce", "returned", "failed"]):
                bounce_count += 1
                bounce_amount += amount
            if any(token in desc for token in ["penalty", "charges", "late fee", "charge"]):
                penalty_count += 1
                penalty_amount += amount

        rows = [
            ("Bounces", bounce_count, bounce_amount),
            ("Penalties", penalty_count, penalty_amount),
        ]
        for row_idx, row in enumerate(rows, 2):
            for col_idx, value in enumerate(row, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20

        return "Bounces & Penal"

    def _create_icici_funds_received_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        return self._create_flow_sheet(workbook, transactions, "Funds Received", incoming=True)

    def _create_icici_funds_remittance_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        return self._create_flow_sheet(workbook, transactions, "Funds Remittance", incoming=False)

    def _create_flow_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]], title: str, incoming: bool) -> str:
        ws = workbook.create_sheet(title)
        headers = ["Category", "Count", "Total Amount"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="2F75B5", end_color="2F75B5", fill_type="solid")

        buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "total": 0.0})
        for txn in transactions:
            amount = float(txn.get("amount", 0) or 0)
            is_credit = str(txn.get("type", "")).lower() == "credit"
            if incoming != is_credit:
                continue
            category = str(txn.get("category", "Other") or "Other")
            buckets[category]["count"] += 1
            buckets[category]["total"] += amount

        for row, (category, data) in enumerate(sorted(buckets.items(), key=lambda item: item[1]["total"], reverse=True), 2):
            ws.cell(row=row, column=1, value=category)
            ws.cell(row=row, column=2, value=data["count"])
            ws.cell(row=row, column=3, value=data["total"])

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

        return title

    def _apply_icici_styling(self, worksheet):
        if worksheet.max_row < 1:
            return
        for col in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=1, column=col)
            if cell.value:
                cell.font = Font(color="FFFFFF", bold=True)
                if worksheet.title == "Bounces & Penal":
                    cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
