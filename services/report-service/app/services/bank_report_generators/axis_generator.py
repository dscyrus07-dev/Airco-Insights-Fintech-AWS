"""
Axis Bank report generator implementation.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)


class AxisReportGenerator(BaseBankReportGenerator):
    """Axis Bank report generator."""

    def __init__(self):
        super().__init__("axis")

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
        sheets_created.append(self._create_axis_weekly_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_axis_source_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_axis_category_outcome_sheet(workbook, transactions))

        for sheet_name in sheets_created:
            if sheet_name in workbook.sheetnames:
                self._apply_axis_styling(workbook[sheet_name])

        logger.info("Axis report sheets generated", sheets=sheets_created)
        return sheets_created

    def _create_axis_weekly_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Weekly Analysis")
        headers = ["Week", "Credits", "Debits", "Net Flow", "Transactions"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

        weekly = defaultdict(lambda: {"credits": 0, "debits": 0, "count": 0})
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

    def _create_axis_source_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Source Analysis")
        headers = ["Source Type", "Transaction Count", "Total Amount", "Average Amount"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")

        source_patterns: Dict[str, Dict[str, float]] = {}
        for txn in transactions:
            desc = str(txn.get("description", "")).lower()
            amount = float(txn.get("amount", 0) or 0)
            if "upi" in desc:
                source = "UPI"
            elif "atm" in desc:
                source = "ATM"
            elif "neft" in desc or "rtgs" in desc:
                source = "NEFT/RTGS"
            elif "imps" in desc:
                source = "IMPS"
            elif "cheque" in desc or "chq" in desc:
                source = "Cheque"
            elif "ach" in desc or "nach" in desc:
                source = "ACH/NACH"
            else:
                source = "Other"
            if source not in source_patterns:
                source_patterns[source] = {"count": 0, "total": 0.0}
            source_patterns[source]["count"] += 1
            source_patterns[source]["total"] += amount

        for row, (source, data) in enumerate(sorted(source_patterns.items(), key=lambda item: item[1]["total"], reverse=True), 2):
            count = data["count"]
            total = data["total"]
            ws.cell(row=row, column=1, value=source)
            ws.cell(row=row, column=2, value=count)
            ws.cell(row=row, column=3, value=total)
            ws.cell(row=row, column=4, value=(total / count) if count else 0)

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20

        return "Source Analysis"

    def _create_axis_category_outcome_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Category Outcome")
        headers = ["Category", "Transactions", "Credits", "Debits", "Net Outcome", "Trend"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")

        category_outcomes: Dict[str, Dict[str, float]] = {}
        for txn in transactions:
            category = str(txn.get("category", "Uncategorized") or "Uncategorized")
            amount = float(txn.get("amount", 0) or 0)
            txn_type = str(txn.get("type", "")).lower()
            if category not in category_outcomes:
                category_outcomes[category] = {"credits": 0.0, "debits": 0.0, "count": 0}
            category_outcomes[category]["count"] += 1
            if txn_type == "credit":
                category_outcomes[category]["credits"] += amount
            else:
                category_outcomes[category]["debits"] += amount

        for row, (category, data) in enumerate(sorted(category_outcomes.items(), key=lambda item: item[1]["credits"] - item[1]["debits"], reverse=True), 2):
            net = data["credits"] - data["debits"]
            trend = "Positive" if net > 0 else "Negative" if net < 0 else "Neutral"
            ws.cell(row=row, column=1, value=category)
            ws.cell(row=row, column=2, value=data["count"])
            ws.cell(row=row, column=3, value=data["credits"])
            ws.cell(row=row, column=4, value=data["debits"])
            ws.cell(row=row, column=5, value=net)
            ws.cell(row=row, column=6, value=trend)

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

        return "Category Outcome"

    def _apply_axis_styling(self, worksheet):
        if worksheet.max_row < 1:
            return
        for col in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=1, column=col)
            if not cell.value:
                continue
            cell.font = Font(color="FFFFFF", bold=True)
            if worksheet.title == "Source Analysis":
                cell.fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")
            elif worksheet.title == "Category Outcome":
                cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
            else:
                cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
