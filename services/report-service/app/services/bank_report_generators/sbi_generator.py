"""
SBI Bank report generator implementation.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)


class SBIReportGenerator(BaseBankReportGenerator):
    """SBI Bank report generator."""

    def __init__(self):
        super().__init__("sbi")

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
        sheets_created.append(self._create_sbi_weekly_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_sbi_finbit_sheet(workbook, transactions))
        sheets_created.append(self._create_sbi_raw_transaction_sheet(workbook, transactions))

        for sheet_name in sheets_created:
            if sheet_name in workbook.sheetnames:
                self._apply_sbi_styling(workbook[sheet_name])

        logger.info("SBI report sheets generated", sheets=sheets_created)
        return sheets_created

    def _create_sbi_weekly_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Weekly Analysis")
        headers = ["Week", "Credits", "Debits", "Net Flow", "Transactions"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

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

    def _create_sbi_finbit_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Finbit")
        headers = ["Metric", "Value"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

        total_credits = sum(float(txn.get("amount", 0) or 0) for txn in transactions if str(txn.get("type", "")).lower() == "credit")
        total_debits = sum(float(txn.get("amount", 0) or 0) for txn in transactions if str(txn.get("type", "")).lower() == "debit")
        rows = [
            ("Total Transactions", len(transactions)),
            ("Total Credits", total_credits),
            ("Total Debits", total_debits),
            ("Net Flow", total_credits - total_debits),
        ]
        for row_idx, row in enumerate(rows, 2):
            ws.cell(row=row_idx, column=1, value=row[0])
            ws.cell(row=row_idx, column=2, value=row[1])

        ws.column_dimensions["A"].width = 24
        ws.column_dimensions["B"].width = 18
        return "Finbit"

    def _create_sbi_raw_transaction_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        ws = workbook.create_sheet("Raw Transaction")
        headers = ["Date", "Description", "Amount", "Type", "Category", "Confidence"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")

        for row_idx, txn in enumerate(transactions, 2):
            ws.cell(row=row_idx, column=1, value=txn.get("date", ""))
            ws.cell(row=row_idx, column=2, value=txn.get("description", ""))
            ws.cell(row=row_idx, column=3, value=txn.get("amount", 0))
            ws.cell(row=row_idx, column=4, value=txn.get("type", ""))
            ws.cell(row=row_idx, column=5, value=txn.get("category", ""))
            ws.cell(row=row_idx, column=6, value=txn.get("confidence", ""))

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

        return "Raw Transaction"

    def _apply_sbi_styling(self, worksheet):
        if worksheet.max_row < 1:
            return
        for col in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=1, column=col)
            if cell.value:
                cell.font = Font(color="FFFFFF", bold=True)
                if worksheet.title == "Finbit":
                    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="7030A0", end_color="7030A0", fill_type="solid")
