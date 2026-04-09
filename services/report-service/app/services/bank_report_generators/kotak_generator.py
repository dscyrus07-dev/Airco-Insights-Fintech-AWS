"""
Kotak Bank report generator implementation.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)


class KotakReportGenerator(BaseBankReportGenerator):
    """Kotak Bank report generator."""

    def __init__(self):
        super().__init__("kotak")

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
        sheets_created.append(self._create_kotak_weekly_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_kotak_monthly_stats_sheet(workbook, transactions))
        sheets_created.append(self._create_kotak_funds_remittance_sheet(workbook, transactions))

        for sheet_name in sheets_created:
            if sheet_name in workbook.sheetnames:
                self._apply_kotak_styling(workbook[sheet_name])

        logger.info("Kotak report sheets generated", sheets=sheets_created)
        return sheets_created

    def _create_kotak_weekly_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Weekly Analysis")
        headers = ["Week", "Credits", "Debits", "Net Flow", "Transactions"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")

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

    def _create_kotak_monthly_stats_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Monthly Stats")
        headers = ["Month", "Transactions", "Credits", "Debits", "Net Flow"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

        monthly = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0})
        for txn in transactions:
            date = str(txn.get("date", ""))
            month = date[:7] if len(date) >= 7 else "Unknown"
            amount = float(txn.get("amount", 0) or 0)
            txn_type = str(txn.get("type", "")).lower()
            monthly[month]["count"] += 1
            if txn_type == "credit":
                monthly[month]["credits"] += amount
            else:
                monthly[month]["debits"] += amount

        for row, (month, data) in enumerate(sorted(monthly.items()), 2):
            ws.cell(row=row, column=1, value=month)
            ws.cell(row=row, column=2, value=data["count"])
            ws.cell(row=row, column=3, value=data["credits"])
            ws.cell(row=row, column=4, value=data["debits"])
            ws.cell(row=row, column=5, value=data["credits"] - data["debits"])

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

        return "Monthly Stats"

    def _create_kotak_funds_remittance_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Funds Remittance")
        headers = ["Category", "Count", "Total Amount"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")

        outflows: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "total": 0.0})
        for txn in transactions:
            if str(txn.get("type", "")).lower() != "debit":
                continue
            category = str(txn.get("category", "Other") or "Other")
            amount = float(txn.get("amount", 0) or 0)
            outflows[category]["count"] += 1
            outflows[category]["total"] += amount

        for row, (category, data) in enumerate(sorted(outflows.items(), key=lambda item: item[1]["total"], reverse=True), 2):
            ws.cell(row=row, column=1, value=category)
            ws.cell(row=row, column=2, value=data["count"])
            ws.cell(row=row, column=3, value=data["total"])

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

        return "Funds Remittance"

    def _apply_kotak_styling(self, worksheet):
        if worksheet.max_row < 1:
            return
        for col in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=1, column=col)
            if cell.value:
                cell.font = Font(color="FFFFFF", bold=True)
                if worksheet.title == "Funds Remittance":
                    cell.fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")
