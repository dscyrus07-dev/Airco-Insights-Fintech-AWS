"""
Formula-Based Excel Report Engine
==================================
Generates Excel reports using ONLY Excel formulas for all calculations.
No hardcoded numeric values - everything is formula-driven.

Column Mapping (FIXED - DO NOT CHANGE):
  Column A = Date         (date values)
  Column B = Description  (text)
  Column C = Debit        (numeric — blank if no debit)
  Column D = Credit       (numeric — blank if no credit)
  Column E = Balance      (numeric)
  Column F = Category     (text)
  Column G = Confidence   (text or %)
  Column H = Recurring    (text: "Yes" or "No")

ABSOLUTE RULES:
  - Column D (Credit) = ONLY source for ALL credit calculations
  - Column C (Debit) = ONLY source for ALL debit calculations
  - NEVER infer credit/debit from Description or Balance
  - Blank cell = zero. Never skip. Never guess.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from calendar import monthrange
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill, NamedStyle
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

from app.services.banks._shared.category_registry import normalize_category

from .report_generator import (
    CHEQUE_TOKENS,
    _build_category_outcome_frame,
    _build_source_analysis_frame,
    _build_category_outcome_tables,
    _compute_finbit_monthly,
    get_classifier,
    get_week_bucket,
)


class SBIFormulaExcelEngine:
    """
    Excel report generator using 100% Excel formulas.
    No Python-calculated values in output sheets.
    """
    
    # Fixed column mapping
    COL_DATE = 'A'
    COL_DESC = 'B'
    COL_DEBIT = 'C'
    COL_CREDIT = 'D'
    COL_BALANCE = 'E'
    COL_CATEGORY = 'F'
    COL_CONFIDENCE = 'G'
    COL_RECURRING = 'H'
    
    # Sheet name
    RAW_SHEET = 'Raw Transaction'
    
    # Styles
    FONT_DEFAULT = Font(name='Arial', size=10)
    FONT_BOLD = Font(name='Arial', size=10, bold=True)
    FONT_HEADER = Font(name='Arial', size=10, bold=True)
    FONT_HEADER_WHITE = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    
    ALIGN_LEFT = Alignment(horizontal='left', vertical='center')
    ALIGN_CENTER = Alignment(horizontal='center', vertical='center')
    ALIGN_RIGHT = Alignment(horizontal='right', vertical='center')
    
    BORDER_THIN = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    FILL_LIGHT_BLUE = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    FILL_HDFC_BLUE = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    FILL_LIGHT_ORANGE = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
    FILL_QUALITY_HIGH = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    FILL_QUALITY_MEDIUM = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    FILL_QUALITY_LOW = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    
    # Number formats
    FMT_CURRENCY = '₹#,##0.00'
    FMT_INTEGER = '#,##0'
    FMT_DATE = 'DD-MM-YYYY'
    
    def __init__(self):
        self.workbook = None
        self.last_row = 0
        self.months: List[Tuple[int, int]] = []

    @staticmethod
    def _col_letter(index: int) -> str:
        """Convert a 1-based column index to an Excel column letter."""
        return get_column_letter(index)

    def _style_section_header(self, ws, row: int, start_col: int, end_col: int, title: str, fill=None):
        ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=end_col)
        cell = ws.cell(row, start_col, title)
        cell.font = self.FONT_HEADER_WHITE
        cell.fill = fill or self.FILL_HDFC_BLUE
        cell.alignment = self.ALIGN_LEFT
        cell.border = self.BORDER_THIN
        for col in range(start_col + 1, end_col + 1):
            ws.cell(row, col).fill = fill or self.FILL_HDFC_BLUE
            ws.cell(row, col).border = self.BORDER_THIN

    def _style_header_row(self, ws, row: int, start_col: int, end_col: int, fill=None, font=None):
        for col in range(start_col, end_col + 1):
            cell = ws.cell(row, col)
            cell.font = font or self.FONT_HEADER_WHITE
            cell.fill = fill or self.FILL_HDFC_BLUE
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN

    @staticmethod
    def _confidence_to_int(value: Any) -> int:
        try:
            conf = float(value or 0)
        except (TypeError, ValueError):
            return 0
        if 0 <= conf <= 1:
            conf *= 100
        return int(round(conf))

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip().upper()

    def _map_hdfc_category(self, description: Any, category: Any, debit: Any, credit: Any) -> str:
        desc = self._normalize_text(description)
        existing = str(category or "").strip()
        existing_upper = existing.upper()
        is_credit = float(credit or 0) > 0 and float(debit or 0) <= 0
        is_debit = float(debit or 0) > 0 and float(credit or 0) <= 0

        if is_credit:
            if any(k in desc for k in ["SALARY", "SAL CR", "PAYROLL", "WAGES", "STIPEND"]):
                return "Salary"
            if any(k in desc for k in ["CASH DEPOSIT", "CDM", "CASHDEP", "CASH DEP"]):
                return "Cash Deposit"
            if any(k in desc for k in ["INTEREST", "INT CR", "INTEREST CREDIT"]):
                return "Interest"
            if any(k in desc for k in ["REFUND", "REVERSAL", "REVERSE", "RETURN"]):
                return "Refund"
            if any(k in desc for k in ["LOAN DISB", "DISBURSE", "LOAN CREDIT"]):
                return "Loan Disbursal"
            if "UPI" in desc:
                return "UPI Transfer"
            if any(k in desc for k in ["NEFT", "IMPS", "RTGS", "ACH", "TRANSFER", "TRF"]):
                return "Bank Transfer"
            if any(k in desc for k in ["CHEQUE", "CHQ", "CLG"]):
                return "Cheque Deposit"
            if "BUSINESS" in existing_upper:
                return "Business Expense"
            return "Others Credit"

        if is_debit:
            if any(k in desc for k in ["EMI", "LOAN REPAY", "LOAN PAYMENT", "INSTALLMENT", "INSTALMENT", "CREDIT CARD", "CC PAYMENT"]):
                return "Loan Payment / EMI"
            if "ATM" in desc:
                return "ATM Withdrawal"
            if "UPI" in desc:
                return "UPI Transfer"
            if any(k in desc for k in ["NEFT", "IMPS", "RTGS", "ACH", "TRANSFER", "TRF"]):
                return "Transfer Out"
            if any(k in desc for k in ["BILL", "ELECTRIC", "WATER", "GAS", "RECHARGE", "SUBSCRIPTION", "CHARGE", "GST", "SMS ALERT"]):
                return "Bill Payment"
            if any(k in desc for k in ["TRAVEL", "UBER", "OLA", "FLIGHT", "HOTEL", "IRCTC"]):
                return "Travel Expense"
            if any(k in desc for k in ["FOOD", "SWIGGY", "ZOMATO", "RESTAURANT", "CAFE"]):
                return "Food"
            if any(k in desc for k in ["SHOP", "AMAZON", "FLIPKART", "MYNTRA", "AJIO"]):
                return "Shopping"
            if any(k in desc for k in ["PETROL", "DIESEL", "FUEL", "TRANSPORT", "CAB", "BUS", "TRAIN"]):
                return "Transport"
            if any(k in desc for k in ["BANK CHARGE", "PENAL", "BOUNCE", "RETURN"]):
                return "Business Expense"
            return "Others Debit"

        return existing or "Others Credit"

    @staticmethod
    def _first_day_balance(month_df: pd.DataFrame, month_start: pd.Timestamp) -> float:
        day_one = month_df[month_df["Date"].dt.normalize() == month_start.normalize()]
        if len(day_one) > 0:
            return float(day_one.iloc[-1]["Balance"])
        prior = month_df[month_df["Date"] < month_start]
        if len(prior) > 0:
            return float(prior.iloc[-1]["Balance"])
        return float(month_df.iloc[0]["Balance"]) if len(month_df) > 0 else 0.0

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None,
        output_path: str = None
    ) -> bytes:
        """
        Generate Excel report with formula-based calculations.
        
        Args:
            transactions: List of transaction dicts with keys:
                date, description, debit, credit, balance, category, confidence, recurring
            metadata: Optional dict with name, account_no
            output_path: Optional file path to save
            
        Returns:
            Excel file bytes
        """
        self.workbook = Workbook()
        metadata = metadata or {}
        self._ctx = self._prepare_report_context(transactions, metadata)
        
        # Calculate last_row (header + data rows)
        self.last_row = len(self._ctx["df"]) + 1
        
        # Create sheets in order
        # Remove default sheet first
        default_sheet = self.workbook.active
        
        # Create all sheets in HDFC-style order
        ws_summary = self.workbook.create_sheet("Summary", 0)
        ws_monthly = self.workbook.create_sheet("Monthly Analysis", 1)
        ws_weekly = self.workbook.create_sheet("Weekly Analysis", 2)
        ws_category = self.workbook.create_sheet("Category Analysis", 3)
        ws_bounces = self.workbook.create_sheet("Bounces & Penal", 4)
        ws_received = self.workbook.create_sheet("Funds Received", 5)
        ws_remittance = self.workbook.create_sheet("Funds Remittance", 6)
        ws_raw = self.workbook.create_sheet(self.RAW_SHEET, 7)
        ws_source = self.workbook.create_sheet("Source Analysis", 8)
        ws_outcome = self.workbook.create_sheet("Category Outcome", 9)
        ws_finbit = self.workbook.create_sheet("Finbit", 10)
        
        # Remove default sheet
        self.workbook.remove(default_sheet)

        # Sheet tab colors to match the HDFC workbook feel
        for ws in (ws_summary, ws_monthly, ws_weekly, ws_category, ws_bounces, ws_received, ws_remittance, ws_raw, ws_source, ws_outcome, ws_finbit):
            ws.sheet_properties.tabColor = "1F4E79"
        
        # Build sheets
        self._build_raw_transactions(ws_raw, transactions)
        self._build_summary(ws_summary, metadata)
        self._build_monthly_analysis(ws_monthly, transactions)
        self._build_weekly_analysis(ws_weekly)
        self._build_category_analysis(ws_category)
        self._build_bounces_and_penal(ws_bounces, transactions, metadata)
        self._build_funds_received(ws_received, transactions)
        self._build_funds_remittance(ws_remittance, transactions)
        self._build_source_analysis(ws_source, transactions)
        self._build_category_outcome(ws_outcome, transactions)
        self._build_finbit(ws_finbit, transactions)

        # Apply a consistent HDFC visual theme to primary headers
        self._apply_hdfc_theme(ws_summary)
        self._apply_hdfc_theme(ws_monthly)
        self._apply_hdfc_theme(ws_weekly)
        self._apply_hdfc_theme(ws_category)
        self._apply_hdfc_theme(ws_bounces)
        self._apply_hdfc_theme(ws_received)
        self._apply_hdfc_theme(ws_remittance)
        self._apply_hdfc_theme(ws_raw)
        self._apply_hdfc_theme(ws_source)
        self._apply_hdfc_theme(ws_outcome)
        self._apply_hdfc_theme(ws_finbit)
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        self.workbook.save(buffer)
        buffer.seek(0)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
        
        return buffer.getvalue()

    def _apply_hdfc_theme(self, ws):
        """Apply a consistent HDFC-style theme to a worksheet after it has been populated."""
        if ws.title == 'Summary' and ws.max_row >= 6:
            for cell_ref in ('A1', 'A2', 'A3', 'A4'):
                ws[cell_ref].font = self.FONT_BOLD
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(6, col)
                cell.fill = self.FILL_HDFC_BLUE
                cell.font = self.FONT_HEADER_WHITE
                cell.alignment = self.ALIGN_CENTER
                cell.border = self.BORDER_THIN
            for row in range(7, ws.max_row + 1):
                ws.cell(row, 1).font = self.FONT_BOLD

        elif ws.title == 'Monthly Analysis' and ws.max_row >= 1:
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(1, col)
                cell.fill = self.FILL_HDFC_BLUE
                cell.font = self.FONT_HEADER_WHITE
                cell.border = self.BORDER_THIN
            for row in (2, 38):
                if row <= ws.max_row:
                    for col in range(1, ws.max_column + 1):
                        cell = ws.cell(row, col)
                        if cell.value is not None:
                            cell.fill = self.FILL_HDFC_BLUE
                            cell.font = self.FONT_HEADER_WHITE
                            cell.border = self.BORDER_THIN

        elif ws.title == 'Weekly Analysis' and ws.max_row >= 1:
            for col in range(1, ws.max_column + 1):
                if ws.cell(1, col).value is not None:
                    ws.cell(1, col).fill = self.FILL_HDFC_BLUE
                    ws.cell(1, col).font = self.FONT_HEADER_WHITE
                    ws.cell(1, col).border = self.BORDER_THIN
            for row in range(11, ws.max_row + 1):
                for col in range(1, ws.max_column + 1):
                    if ws.cell(row, col).value is not None and isinstance(ws.cell(row, col).value, str) and ws.cell(row, col).value.startswith('MONTH OVER MONTH'):
                        for c in range(1, ws.max_column + 1):
                            if ws.cell(row, c).value is not None:
                                ws.cell(row, c).fill = self.FILL_HDFC_BLUE
                                ws.cell(row, c).font = self.FONT_HEADER_WHITE
                                ws.cell(row, c).border = self.BORDER_THIN

        elif ws.title in {'Category Analysis', 'Bounces & Penal', 'Funds Received', 'Funds Remittance', 'Category Outcome', 'Finbit'}:
            first_rows = 2
            for row in range(1, min(first_rows, ws.max_row) + 1):
                for col in range(1, ws.max_column + 1):
                    cell = ws.cell(row, col)
                    if cell.value is not None:
                        cell.font = self.FONT_HEADER_WHITE if row == 1 else self.FONT_BOLD
                        cell.fill = self.FILL_HDFC_BLUE
                        cell.border = self.BORDER_THIN
    
    def _extract_months(self, transactions: List[Dict[str, Any]]):
        """Extract unique (year, month) tuples from transactions, sorted chronologically."""
        months_set = set()
        
        for txn in transactions:
            date_val = txn.get('date')
            if date_val:
                try:
                    if isinstance(date_val, str):
                        # Try multiple date formats
                        for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                            try:
                                dt = datetime.strptime(date_val, fmt)
                                months_set.add((dt.year, dt.month))
                                break
                            except ValueError:
                                continue
                    elif isinstance(date_val, datetime):
                        months_set.add((date_val.year, date_val.month))
                except Exception:
                    pass
        
        self.months = sorted(list(months_set))
    
    def _get_last_day(self, year: int, month: int) -> int:
        """Get the last day of a month."""
        return monthrange(year, month)[1]

    def _prepare_report_context(
        self,
        transactions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare HDFC-style analytical frames and aggregates from SBI transactions."""
        df = pd.DataFrame(transactions).copy()
        if len(df) == 0:
            df = pd.DataFrame(columns=["date", "description", "debit", "credit", "balance", "category", "confidence", "recurring"])

        rename_map = {
            "date": "Date",
            "description": "Description",
            "debit": "Debit",
            "credit": "Credit",
            "balance": "Balance",
            "category": "Category",
            "recurring": "Recurring",
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
        for col in ["Date", "Description", "Debit", "Credit", "Balance", "Category", "Recurring"]:
            if col not in df.columns:
                df[col] = "" if col in {"Description", "Category", "Recurring"} else 0

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True, format="mixed")
        df = df[df["Date"].notna()].copy()
        df.sort_values(["Date", "Description"], kind="stable", inplace=True)
        df.reset_index(drop=True, inplace=True)

        df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
        df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)
        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0)
        df["Description"] = df["Description"].fillna("").astype(str)
        df["Category"] = df["Category"].fillna("").astype(str)
        df["Recurring"] = df["Recurring"].fillna("No").astype(str)

        df["Category"] = [
            self._map_hdfc_category(desc, cat, debit, credit)
            for desc, cat, debit, credit in zip(df["Description"], df["Category"], df["Debit"], df["Credit"])
        ]

        df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
        months = sorted(df["Month"].dropna().unique().tolist())

        monthly: Dict[Any, Dict[str, Any]] = {}
        for m in months:
            mdf = df[df["Month"] == m]
            monthly[m] = {
                "credit_count": int((mdf["Credit"] > 0).sum()),
                "credit_amount": float(mdf["Credit"].sum()),
                "debit_count": int((mdf["Debit"] > 0).sum()),
                "debit_amount": float(mdf["Debit"].sum()),
                "avg_balance": float(mdf["Balance"].mean()) if len(mdf) > 0 else 0,
                "min_balance": float(mdf["Balance"].min()) if len(mdf) > 0 else 0,
                "max_balance": float(mdf["Balance"].max()) if len(mdf) > 0 else 0,
                "start_balance": self._first_day_balance(mdf, m),
                "end_balance": float(mdf.iloc[-1]["Balance"]) if len(mdf) > 0 else 0,
            }

        classifier = get_classifier()
        classifier_categories = list(getattr(classifier, 'categories', {}).keys())
        credit_df = df[df["Credit"] > 0]
        debit_df = df[df["Debit"] > 0]

        credit_cats: Dict[str, Dict[str, Any]] = {}
        for cat in sorted(set(classifier_categories) | set(credit_df["Category"].unique().tolist())):
            cdf = credit_df[credit_df["Category"] == cat]
            if len(cdf) > 0:
                credit_cats[cat] = {"amount": float(cdf["Credit"].sum()), "count": len(cdf)}

        debit_cats: Dict[str, Dict[str, Any]] = {}
        for cat in sorted(set(classifier_categories) | set(debit_df["Category"].unique().tolist())):
            ddf = debit_df[debit_df["Category"] == cat]
            if len(ddf) > 0:
                debit_cats[cat] = {"amount": float(ddf["Debit"].sum()), "count": len(ddf)}

        def _is_cheque(desc: str) -> bool:
            desc_lower = str(desc).lower()
            return any(tok in desc_lower for tok in CHEQUE_TOKENS)

        df["IsCheque"] = df["Description"].apply(_is_cheque)
        df["WeekBucket"] = df["Date"].apply(get_week_bucket)

        week_order = [
            "Week 1 (1-5)", "Week 2 (6-10)", "Week 3 (11-15)",
            "Week 4 (16-20)", "Week 5 (21-25)", "Week 6 (26-end)",
        ]

        weekly_credit = {}
        weekly_debit = {}
        for w in week_order:
            wc = df[(df["WeekBucket"] == w) & (df["Credit"] > 0)]
            wd = df[(df["WeekBucket"] == w) & (df["Debit"] > 0)]
            weekly_credit[w] = {"amount": float(wc["Credit"].sum()), "count": len(wc)}
            weekly_debit[w] = {"amount": float(wd["Debit"].sum()), "count": len(wd)}

        monthly_weekly_credit = {}
        monthly_weekly_debit = {}
        for m in months:
            mdf = df[df["Month"] == m]
            monthly_weekly_credit[m] = {}
            monthly_weekly_debit[m] = {}
            for w in week_order:
                wc = mdf[(mdf["WeekBucket"] == w) & (mdf["Credit"] > 0)]
                wd = mdf[(mdf["WeekBucket"] == w) & (mdf["Debit"] > 0)]
                monthly_weekly_credit[m][w] = {"amount": float(wc["Credit"].sum()), "count": len(wc)}
                monthly_weekly_debit[m][w] = {"amount": float(wd["Debit"].sum()), "count": len(wd)}

        source_df = _build_source_analysis_frame(df.copy())
        source_df = source_df.sort_values(["Date", "Description"], kind="stable").reset_index(drop=True)
        outcome_frame = _build_category_outcome_frame(source_df)
        if len(outcome_frame) > 0:
            outcome_frame = outcome_frame.copy()
            outcome_frame["Month"] = pd.to_datetime(outcome_frame["Month"], errors="coerce")
            month_periods = []
            for period in outcome_frame["Month"].dropna().dt.to_period("M").tolist():
                if period not in month_periods:
                    month_periods.append(period)
            month_periods = sorted(month_periods)[:6]
            month_keys = [period.strftime("%Y-%m") for period in month_periods]
            month_labels = [period.strftime("%B %Y") for period in month_periods]
            outcome_tables = {"month_keys": month_keys, "month_labels": month_labels}

            def _pivot_outcome(kind: str) -> pd.DataFrame:
                if kind == "credit_count":
                    value_col = "CreditCount"
                elif kind == "debit_count":
                    value_col = "DebitCount"
                elif kind == "credit_amount":
                    value_col = "TotalCreditAmount"
                else:
                    value_col = "TotalDebitAmount"
                base = outcome_frame[["Category", "Source", "Month", value_col]].copy()
                base["MonthKey"] = base["Month"].dt.to_period("M").astype(str)
                grouped = base.groupby(["Category", "Source", "MonthKey"], dropna=False)[value_col].sum().reset_index()
                pivot = grouped.pivot_table(index=["Category", "Source"], columns="MonthKey", values=value_col, aggfunc="sum", fill_value=0)
                pivot = pivot.reindex(columns=month_keys, fill_value=0).reset_index()
                rename_map = dict(zip(month_keys, month_labels))
                pivot = pivot.rename(columns=rename_map)
                for label in month_labels:
                    if label not in pivot.columns:
                        pivot[label] = 0
                pivot = pivot[["Category", "Source", *month_labels]]
                pivot["_rank"] = pivot["Category"].map(lambda value: 2 if value == "Flag" else (1 if value == "Others" else 0))
                pivot["_source_sort"] = pivot["Source"].fillna("").astype(str)
                pivot = pivot.sort_values(["_rank", "Category", "_source_sort"], kind="stable").drop(columns=["_rank", "_source_sort"]).reset_index(drop=True)
                return pivot

            outcome_tables["credit_count"] = _pivot_outcome("credit_count")
            outcome_tables["debit_count"] = _pivot_outcome("debit_count")
            outcome_tables["credit_amount"] = _pivot_outcome("credit_amount")
            outcome_tables["debit_amount"] = _pivot_outcome("debit_amount")
        else:
            outcome_tables = {"month_keys": [], "month_labels": []}
        opening_balance = float(df.iloc[0]["Balance"] - df.iloc[0]["Credit"] + df.iloc[0]["Debit"]) if len(df) > 0 else 0
        finbit_months, finbit_data = _compute_finbit_monthly(df, opening_balance)

        return {
            "df": df,
            "months": months,
            "monthly": monthly,
            "credit_cats": credit_cats,
            "debit_cats": debit_cats,
            "weekly_credit": weekly_credit,
            "weekly_debit": weekly_debit,
            "monthly_weekly_credit": monthly_weekly_credit,
            "monthly_weekly_debit": monthly_weekly_debit,
            "source_df": source_df,
            "outcome_tables": outcome_tables,
            "finbit_months": finbit_months,
            "finbit_data": finbit_data,
        }
    
    def _build_raw_transactions(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Raw Transactions sheet with source data."""
        # Headers
        headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category', 'Confidence', 'Recurring']
        ws.row_dimensions[1].height = 18
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.FONT_HEADER_WHITE
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            cell.fill = self.FILL_HDFC_BLUE
        
        # Data rows - set formatted values and apply white fill immediately
        for row_idx, txn in enumerate(transactions, 2):
            # Helper function to create properly styled cell
            def style_cell(row, col, value):
                c = ws.cell(row=row, column=col, value=value)
                c.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
                c.font = Font(name='Arial', size=10, bold=False)
                c.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
                return c
            
            # Column A - Date (formatted as string)
            date_val = txn.get('date', '')
            if isinstance(date_val, datetime):
                date_str = date_val.strftime('%d-%m-%Y')
            elif isinstance(date_val, str):
                date_str = date_val
            else:
                date_str = ''
            style_cell(row_idx, 1, date_str)
            
            # Column B - Description
            style_cell(row_idx, 2, txn.get('description', ''))
            
            # Column C - Debit (formatted as currency string)
            debit = txn.get('debit')
            if debit is not None and debit > 0:
                style_cell(row_idx, 3, f"₹{debit:,.2f}")
            else:
                style_cell(row_idx, 3, '')
            
            # Column D - Credit (formatted as currency string)
            credit = txn.get('credit')
            if credit is not None and credit > 0:
                style_cell(row_idx, 4, f"₹{credit:,.2f}")
            else:
                style_cell(row_idx, 4, '')
            
            # Column E - Balance (formatted as currency string)
            balance = txn.get('balance')
            if balance is not None:
                style_cell(row_idx, 5, f"₹{balance:,.2f}")
            else:
                style_cell(row_idx, 5, '')
            
            # Column F - Category
            style_cell(row_idx, 6, self._map_hdfc_category(txn.get('description', ''), txn.get('category', ''), txn.get('debit', 0), txn.get('credit', 0)))
            
            # Column G - Confidence
            style_cell(row_idx, 7, self._confidence_to_int(txn.get('confidence', '')))
            
            # Column H - Recurring
            style_cell(row_idx, 8, txn.get('recurring', 'No'))
        
        # Column widths
        ws.column_dimensions['A'].width = 14
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 14
        ws.column_dimensions['H'].width = 13
        
        # Freeze header row
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = f"A1:H{self.last_row}"

    def _parse_txn_date(self, date_val: Any):
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_val, fmt)
                except ValueError:
                    continue
        return None

    def _build_monthly_analysis(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Monthly Analysis sheet matching the HDFC report structure."""
        ctx = self._ctx
        df = ctx['df']
        months = ctx['months']
        monthly = ctx['monthly']
        credit_display = [
            ('Bank Transfer', {'Bank Transfer'}),
            ('Business Expense', {'Business Expense'}),
            ('Loan Disbursal', {'Loan Disbursal'}),
            ('UPI Transfer', {'UPI Transfer'}),
        ]
        debit_display = [
            ('Loan Payment / EMI', {'Loan Payment / EMI'}),
            ('Transfer Out', {'Transfer Out'}),
            ('Travel Expense', {'Travel Expense'}),
            ('Food', {'Food'}),
            ('UPI Transfer', {'UPI Transfer'}),
        ]

        ws.row_dimensions[1].height = 18
        ws.cell(1, 1, 'Metric / Category').font = self.FONT_HEADER_WHITE
        ws.cell(1, 1).border = self.BORDER_THIN
        ws.cell(1, 1).fill = self.FILL_HDFC_BLUE
        for i, m in enumerate(months, 2):
            c = ws.cell(1, i, m.strftime('%b %Y'))
            c.font = self.FONT_HEADER_WHITE
            c.alignment = self.ALIGN_CENTER
            c.border = self.BORDER_THIN
            c.fill = self.FILL_HDFC_BLUE

        row = 2
        ws.row_dimensions[row].height = 18
        self._style_section_header(ws, row, 1, len(months) + 2, 'CREDIT ANALYSIS')
        row += 1
        for idx, (label, aliases) in enumerate(credit_display):
            ws.row_dimensions[row].height = 18
            ws.cell(row, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                if label == 'Others Credit':
                    known = set().union(*[a for _, a in credit_display if _ != 'Others Credit'])
                    mdf = df[(df['Month'] == m) & (df['Credit'] > 0) & (~df['Category'].isin(known))]
                else:
                    mdf = df[(df['Month'] == m) & (df['Category'].isin(aliases)) & (df['Credit'] > 0)]
                cell = ws.cell(row, i, float(mdf['Credit'].sum()) if len(mdf) > 0 else 0.0)
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_CURRENCY
            row += 1

        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'Total Credit Count').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        for i, m in enumerate(months, 2):
            cell = ws.cell(row, i, monthly[m]['credit_count'])
            cell.border = self.BORDER_THIN
            cell.number_format = self.FMT_INTEGER
        row += 1
        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'Total Credit Amount').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        for i, m in enumerate(months, 2):
            cell = ws.cell(row, i, monthly[m]['credit_amount'])
            cell.border = self.BORDER_THIN
            cell.number_format = self.FMT_CURRENCY
        row += 1

        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'MoM Credit Change').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        ws.row_dimensions[row + 1].height = 18
        ws.cell(row + 1, 1, 'MoM Credit %').font = self.FONT_BOLD
        ws.cell(row + 1, 1).border = self.BORDER_THIN
        prev_cr = None
        for i, m in enumerate(months, 2):
            cur = monthly[m]['credit_amount']
            if prev_cr is not None:
                ch = cur - prev_cr
                pc = (ch / prev_cr * 100) if prev_cr != 0 else 0
            else:
                ch = 0.0
                pc = 0.0
            # MoM Change - green for positive, red for negative
            c = ws.cell(row, i, ch)
            c.border = self.BORDER_THIN
            c.number_format = self.FMT_CURRENCY
            if ch > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # Light green
            elif ch < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')  # Light red
            # MoM % - green for positive, red for negative
            c = ws.cell(row + 1, i, pc)
            c.border = self.BORDER_THIN
            c.number_format = '0.0%'
            if pc > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # Light green
            elif pc < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')  # Light red
            prev_cr = cur
        row += 3

        ws.row_dimensions[row].height = 18
        self._style_section_header(ws, row, 1, len(months) + 2, 'DEBIT ANALYSIS')
        row += 1
        for idx, (label, aliases) in enumerate(debit_display):
            ws.row_dimensions[row].height = 18
            ws.cell(row, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                if label == 'Others Debit':
                    known = set().union(*[a for _, a in debit_display if _ != 'Others Debit'])
                    mdf = df[(df['Month'] == m) & (df['Debit'] > 0) & (~df['Category'].isin(known))]
                else:
                    mdf = df[(df['Month'] == m) & (df['Category'].isin(aliases)) & (df['Debit'] > 0)]
                cell = ws.cell(row, i, float(mdf['Debit'].sum()) if len(mdf) > 0 else 0.0)
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_CURRENCY
            row += 1

        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'Total Debit Count').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        for i, m in enumerate(months, 2):
            cell = ws.cell(row, i, monthly[m]['debit_count'])
            cell.border = self.BORDER_THIN
            cell.number_format = self.FMT_INTEGER
        row += 1
        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'Total Debit Amount').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        for i, m in enumerate(months, 2):
            cell = ws.cell(row, i, monthly[m]['debit_amount'])
            cell.border = self.BORDER_THIN
            cell.number_format = self.FMT_CURRENCY
        row += 1

        ws.row_dimensions[row].height = 18
        ws.cell(row, 1, 'MoM Debit Change').font = self.FONT_BOLD
        ws.cell(row, 1).border = self.BORDER_THIN
        ws.row_dimensions[row + 1].height = 18
        ws.cell(row + 1, 1, 'MoM Debit %').font = self.FONT_BOLD
        ws.cell(row + 1, 1).border = self.BORDER_THIN
        prev_db = None
        for i, m in enumerate(months, 2):
            cur = monthly[m]['debit_amount']
            if prev_db is not None:
                ch = cur - prev_db
                pc = (ch / prev_db * 100) if prev_db != 0 else 0
            else:
                ch = 0.0
                pc = 0.0
            # MoM Change - green for positive, red for negative
            c = ws.cell(row, i, ch)
            c.border = self.BORDER_THIN
            c.number_format = self.FMT_CURRENCY
            if ch > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # Light green
            elif ch < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')  # Light red
            # MoM % - green for positive, red for negative
            c = ws.cell(row + 1, i, pc)
            c.border = self.BORDER_THIN
            c.number_format = '0.0%'
            if pc > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # Light green
            elif pc < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')  # Light red
            prev_db = cur
        row += 3

        ws.row_dimensions[row].height = 18
        self._style_section_header(ws, row, 1, len(months) + 2, 'CHEQUE ANALYSIS')
        row += 1
        cheque_rows = [
            ('Total No. of Cheque Deposits', 'credit', 'count'),
            ('Total Amount of Cheque Deposits', 'credit', 'amount'),
            ('Total No. of Cheque Issues', 'debit', 'count'),
            ('Total Amount of Cheque Issues', 'debit', 'amount'),
        ]
        for idx, (label, direction, mtype) in enumerate(cheque_rows):
            ws.row_dimensions[row].height = 18
            ws.cell(row, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                if direction == 'credit':
                    mdf = df[(df['Month'] == m) & (df['IsCheque']) & (df['Credit'] > 0)]
                    value = len(mdf) if mtype == 'count' else float(mdf['Credit'].sum())
                else:
                    mdf = df[(df['Month'] == m) & (df['IsCheque']) & (df['Debit'] > 0)]
                    value = len(mdf) if mtype == 'count' else float(mdf['Debit'].sum())
                cell = ws.cell(row, i, value)
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_INTEGER if mtype == 'count' else self.FMT_CURRENCY
            row += 1

        ws.freeze_panes = 'B2'

    def _build_bounces_and_penal(self, ws, transactions: List[Dict[str, Any]], metadata: Dict[str, Any]):
        """Build the Bounces & Penal sheet matching the HDFC layout."""
        df = self._ctx['df']
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 16
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 14
        ws.column_dimensions['F'].width = 55
        ws.column_dimensions['G'].width = 16
        ws.column_dimensions['H'].width = 18
        ws.column_dimensions['I'].width = 16

        headers = ['Sl. No.', 'Bank Name', 'Account Number', 'Date', 'Cheque No.', 'Description', 'Amount', 'Category', 'Balance']
        ws.row_dimensions[1].height = 18
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(1, ci, h)
            cell.font = self.FONT_HEADER_WHITE
            cell.fill = self.FILL_HDFC_BLUE
            cell.border = self.BORDER_THIN

        bounce_keywords = r"bounce|return|dishon|penalty|penal|charges.*chq|charges.*cheque|unpaid|ecs return"
        bounce_df = df[df['Description'].str.lower().str.contains(bounce_keywords, regex=True, na=False)].copy().sort_values('Date')
        bank_name = metadata.get('bank_name', 'SBI')
        acct_num = metadata.get('account_no', '')
        for ri, (_, txn) in enumerate(bounce_df.iterrows(), 2):
            ws.row_dimensions[ri].height = 18
            ws.cell(ri, 1, ri - 1).border = self.BORDER_THIN
            ws.cell(ri, 2, bank_name).border = self.BORDER_THIN
            ws.cell(ri, 3, acct_num).border = self.BORDER_THIN
            if pd.notna(txn['Date']):
                c = ws.cell(ri, 4, txn['Date'].to_pydatetime())
                c.number_format = self.FMT_DATE
            else:
                ws.cell(ri, 4, '').border = self.BORDER_THIN
            desc_lower = str(txn['Description']).lower()
            chq_no = ''
            m = re.search(r'(?:chq|cheque|clg)\s*(?:no\.?\s*)?(\d{6,})', desc_lower)
            if m:
                chq_no = m.group(1)
            ws.cell(ri, 5, chq_no).border = self.BORDER_THIN
            ws.cell(ri, 6, str(txn['Description'])).border = self.BORDER_THIN
            amt = float(txn['Debit'] if txn['Debit'] > 0 else txn['Credit'])
            ws.cell(ri, 7, amt).border = self.BORDER_THIN
            ws.cell(ri, 7).number_format = self.FMT_CURRENCY
            ws.cell(ri, 8, str(txn['Category'])).border = self.BORDER_THIN
            ws.cell(ri, 9, float(txn['Balance'])).border = self.BORDER_THIN
            ws.cell(ri, 9).number_format = self.FMT_CURRENCY

        ws.freeze_panes = 'A2'

    def _build_funds_received(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Funds Received sheet using the HDFC top-5-per-month grouping."""
        df = self._ctx['df']
        months = self._ctx['months']
        ws.column_dimensions['A'].width = 14
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 18
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
        ws.row_dimensions[1].height = 18
        title = ws.cell(1, 1, 'Top 5 Funds Received')
        title.font = self.FONT_HEADER_WHITE
        title.fill = self.FILL_HDFC_BLUE
        title.border = self.BORDER_THIN
        for col in range(2, 4):
            ws.cell(1, col).fill = self.FILL_HDFC_BLUE
            ws.cell(1, col).border = self.BORDER_THIN
        row = 2
        for m in months:
            m_credits = df[(df['Month'] == m) & (df['Credit'] > 0)].nlargest(5, 'Credit')
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            ws.row_dimensions[row].height = 18
            month_cell = ws.cell(row, 1, m.strftime('%b-%y'))
            month_cell.font = self.FONT_HEADER_WHITE
            month_cell.fill = self.FILL_HDFC_BLUE
            month_cell.border = self.BORDER_THIN
            for col in range(2, 4):
                ws.cell(row, col).fill = self.FILL_HDFC_BLUE
                ws.cell(row, col).border = self.BORDER_THIN
            row += 1
            ws.row_dimensions[row].height = 18
            ws.cell(row, 1, 'Date').font = self.FONT_BOLD
            ws.cell(row, 2, 'Description').font = self.FONT_BOLD
            ws.cell(row, 3, 'Amount').font = self.FONT_BOLD
            row += 1
            for _, txn in m_credits.iterrows():
                ws.row_dimensions[row].height = 18
                if pd.notna(txn['Date']):
                    c = ws.cell(row, 1, txn['Date'].to_pydatetime())
                    c.number_format = self.FMT_DATE
                ws.cell(row, 2, str(txn['Description']))
                ws.cell(row, 3, float(txn['Credit']))
                ws.cell(row, 3).number_format = self.FMT_CURRENCY
                row += 1
        ws.freeze_panes = 'A2'

    def _build_funds_remittance(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Funds Remittance sheet using the HDFC top-5-per-month grouping."""
        df = self._ctx['df']
        months = self._ctx['months']
        ws.column_dimensions['A'].width = 14
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 18
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
        ws.row_dimensions[1].height = 18
        title = ws.cell(1, 1, 'Top 5 Funds Remittances')
        title.font = self.FONT_HEADER_WHITE
        title.fill = self.FILL_HDFC_BLUE
        title.border = self.BORDER_THIN
        for col in range(2, 4):
            ws.cell(1, col).fill = self.FILL_HDFC_BLUE
            ws.cell(1, col).border = self.BORDER_THIN
        row = 2
        for m in months:
            m_debits = df[(df['Month'] == m) & (df['Debit'] > 0)].nlargest(5, 'Debit')
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            ws.row_dimensions[row].height = 18
            month_cell = ws.cell(row, 1, m.strftime('%b-%y'))
            month_cell.font = self.FONT_HEADER_WHITE
            month_cell.fill = self.FILL_HDFC_BLUE
            month_cell.border = self.BORDER_THIN
            for col in range(2, 4):
                ws.cell(row, col).fill = self.FILL_HDFC_BLUE
                ws.cell(row, col).border = self.BORDER_THIN
            row += 1
            ws.row_dimensions[row].height = 18
            ws.cell(row, 1, 'Date').font = self.FONT_BOLD
            ws.cell(row, 2, 'Description').font = self.FONT_BOLD
            ws.cell(row, 3, 'Amount').font = self.FONT_BOLD
            row += 1
            for _, txn in m_debits.iterrows():
                ws.row_dimensions[row].height = 18
                if pd.notna(txn['Date']):
                    c = ws.cell(row, 1, txn['Date'].to_pydatetime())
                    c.number_format = self.FMT_DATE
                ws.cell(row, 2, str(txn['Description']))
                ws.cell(row, 3, float(txn['Debit']))
                ws.cell(row, 3).number_format = self.FMT_CURRENCY
                row += 1
        ws.freeze_panes = 'A2'

    def _build_source_analysis(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Source Analysis sheet matching the HDFC layout."""
        source_df = self._ctx['source_df']
        headers = ['Transaction Mode', 'Source', 'Identified Category', 'Flag', 'Date', 'Description', 'Credit', 'Debit', 'Balance']
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        ws.row_dimensions[1].height = 18
        title_cell = ws.cell(1, 1, 'SOURCE ANALYSIS')
        title_cell.font = self.FONT_BOLD
        title_cell.fill = self.FILL_HDFC_BLUE
        title_cell.font = self.FONT_HEADER_WHITE
        for col in range(1, len(headers) + 1):
            ws.cell(1, col).fill = self.FILL_HDFC_BLUE
        ws.row_dimensions[2].height = 18
        for ci, header in enumerate(headers, 1):
            cell = ws.cell(2, ci, header)
            cell.font = self.FONT_HEADER_WHITE
            cell.fill = self.FILL_HDFC_BLUE
            cell.border = self.BORDER_THIN
        for col, width in {"A": 18, "B": 24, "C": 22, "D": 18, "E": 14, "F": 50, "G": 16, "H": 16, "I": 16}.items():
            ws.column_dimensions[col].width = width
        white_fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
        for ri, row in enumerate(source_df.itertuples(index=False), 3):
            for col in range(1, 10):
                cell = ws.cell(ri, col)
                cell.fill = white_fill
                cell.font = self.FONT_DEFAULT
                cell.border = self.BORDER_THIN
            ws.cell(ri, 1, getattr(row, 'TransactionMode', ''))
            ws.cell(ri, 2, getattr(row, 'Source', ''))
            ws.cell(ri, 3, getattr(row, 'IdentifiedCategory', ''))
            ws.cell(ri, 4, getattr(row, 'Flag', ''))
            dt = getattr(row, 'Date', None)
            if pd.notna(dt):
                ws.cell(ri, 5, dt.to_pydatetime()).number_format = self.FMT_DATE
            ws.cell(ri, 6, getattr(row, 'Description', ''))
            credit = float(getattr(row, 'Credit', 0) or 0)
            debit = float(getattr(row, 'Debit', 0) or 0)
            balance = float(getattr(row, 'Balance', 0) or 0)
            if credit > 0:
                ws.cell(ri, 7, credit).number_format = self.FMT_CURRENCY
            if debit > 0:
                ws.cell(ri, 8, debit).number_format = self.FMT_CURRENCY
            ws.cell(ri, 9, balance).number_format = self.FMT_CURRENCY
        ws.freeze_panes = 'A3'
        ws.auto_filter.ref = f"A2:I{max(source_df.shape[0] + 2, 2)}"

    def _build_category_outcome(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Category Outcome sheet matching the HDFC layout."""
        outcome_tables = self._ctx['outcome_tables']
        month_labels = outcome_tables.get('month_labels', [])
        headers = ['Category', 'Source', *month_labels]
        ws.sheet_view.showOutlineSymbols = True
        ws.sheet_properties.outlinePr.summaryBelow = True
        ws.sheet_properties.outlinePr.summaryRight = False
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 24
        for idx in range(3, 3 + len(month_labels)):
            ws.column_dimensions[self._col_letter(idx)].width = 14

        def _write_table(start_row: int, title: str, table_name: str) -> int:
            table = outcome_tables.get(table_name)
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=len(headers))
            ws.row_dimensions[start_row].height = 18
            title_cell = ws.cell(start_row, 1, title)
            title_cell.font = self.FONT_BOLD
            title_cell.fill = self.FILL_HDFC_BLUE
            title_cell.font = self.FONT_HEADER_WHITE
            title_cell.alignment = self.ALIGN_LEFT
            title_cell.border = self.BORDER_THIN
            for col in range(1, len(headers) + 1):
                cell = ws.cell(start_row, col)
                cell.fill = self.FILL_HDFC_BLUE
                cell.border = self.BORDER_THIN
            header_row = start_row + 1
            ws.row_dimensions[header_row].height = 18
            for ci, header in enumerate(headers, 1):
                cell = ws.cell(header_row, ci, header)
                cell.font = self.FONT_BOLD
                cell.fill = self.FILL_HDFC_BLUE
                cell.font = self.FONT_HEADER_WHITE
                cell.alignment = self.ALIGN_CENTER
                cell.border = self.BORDER_THIN
            data_row = header_row + 1
            if table is None or table.empty:
                return data_row
            current_row = data_row
            category_order = []
            for category in table['Category'].fillna('').astype(str).tolist():
                if category not in category_order:
                    category_order.append(category)
            for category in category_order:
                category_rows = table[table['Category'] == category].copy()
                month_totals = [float(category_rows[month_label].fillna(0).sum()) for month_label in month_labels]
                if not any(value != 0 for value in month_totals):
                    continue
                subtotal_values = {month_label: float(category_rows[month_label].fillna(0).sum()) for month_label in month_labels}
                ws.cell(current_row, 1, category or 'Others').font = self.FONT_BOLD
                ws.cell(current_row, 2, 'All Sources').font = self.FONT_BOLD
                for ci, month_label in enumerate(month_labels, 3):
                    value = subtotal_values.get(month_label, 0)
                    cell = ws.cell(current_row, ci, float(value or 0))
                    cell.number_format = self.FMT_INTEGER if 'Count' in title else self.FMT_CURRENCY
                    cell.border = self.BORDER_THIN
                ws.row_dimensions[current_row].outlineLevel = 0
                current_row += 1
                for _, row in category_rows.sort_values(['Source'], kind='stable').iterrows():
                    if not any(float(row.get(month_label, 0) or 0) != 0 for month_label in month_labels):
                        continue
                    ws.cell(current_row, 1, row.get('Category', ''))
                    ws.cell(current_row, 2, row.get('Source', ''))
                    for ci, month_label in enumerate(month_labels, 3):
                        value = row.get(month_label, 0)
                        if value:
                            cell = ws.cell(current_row, ci, float(value))
                            cell.number_format = self.FMT_INTEGER if 'Count' in title else self.FMT_CURRENCY
                            cell.border = self.BORDER_THIN
                        else:
                            ws.cell(current_row, ci).border = self.BORDER_THIN
                    ws.row_dimensions[current_row].hidden = True
                    ws.row_dimensions[current_row].outlineLevel = 1
                    current_row += 1
            return current_row

        next_row = 1
        next_row = _write_table(next_row, 'CATEGORY OUTCOME  Credit Count', 'credit_count') + 1
        next_row = _write_table(next_row, 'CATEGORY OUTCOME  Debit Count', 'debit_count') + 1
        next_row = _write_table(next_row, 'CATEGORY OUTCOME  Credit Amount', 'credit_amount') + 1
        _write_table(next_row, 'CATEGORY OUTCOME  Debit Amount', 'debit_amount')
        ws.freeze_panes = 'A3'

    def _build_finbit(self, ws, transactions: List[Dict[str, Any]]):
        """Build the Finbit sheet matching the HDFC analysis layout."""
        df = self._ctx['df']
        if len(df) == 0:
            return
        opening_balance = float(df.iloc[0]['Balance'] - df.iloc[0]['Credit'] + df.iloc[0]['Debit']) if len(df) > 0 else 0
        finbit_months, finbit_data = _compute_finbit_monthly(df, opening_balance)
        if not finbit_months or not finbit_data:
            return
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(finbit_months) + 1)
        ws.row_dimensions[1].height = 18
        title_cell = ws.cell(1, 1, 'FINBIT ANALYSIS')
        title_cell.font = self.FONT_HEADER_WHITE
        title_cell.fill = self.FILL_HDFC_BLUE
        for col in range(1, len(finbit_months) + 2):
            ws.cell(1, col).fill = self.FILL_HDFC_BLUE
        ws.row_dimensions[2].height = 18
        metric_cell = ws.cell(2, 1, 'Metric')
        metric_cell.font = self.FONT_HEADER_WHITE
        metric_cell.fill = self.FILL_HDFC_BLUE
        for ci, month_key in enumerate(finbit_months, 2):
            cell = ws.cell(2, ci, month_key)
            cell.font = self.FONT_HEADER_WHITE
            cell.fill = self.FILL_HDFC_BLUE
        finbit_rows = [
            ('monthlyAvgBal', 'Monthly Avg Balance', True), ('maxBalance', 'Max Balance', True), ('minBalance', 'Min Balance', True),
            ('cashDeposit', 'Cash Deposits', True), ('cashWithdrawals', 'Cash Withdrawals', True), ('chqDeposit', 'Cheque Deposits', True),
            ('chqIssues', 'Cheques Issued', True), ('credits', 'Total Credits', True), ('debits', 'Total Debits', True),
            ('inwBounce', 'Inward Bounce', False), ('outwBounce', 'Outward Bounce', False), ('penaltyCharges', 'Penalty Charges', True),
            ('ecsNach', 'ECS / NACH', True), ('totalNetDebit', 'Total Net Debit', True), ('totalNetCredit', 'Total Net Credit', True),
            ('selfWithdraw', 'Self Withdrawal', True), ('selfDeposit', 'Self Deposit', True), ('loanRepayment', 'Loan Repayment', True),
            ('loanCredit', 'Loan Credit', True), ('creditCardPayment', 'Credit Card Payment', True), ('minCredits', 'Min Credit Amount', True),
            ('maxCredits', 'Max Credit Amount', True), ('salary', 'Salary', True), ('bankCharges', 'Bank Charges', True),
            None, ('balanceOpening', 'BALANCE (Opening)', True), ('balanceClosing', 'BALANCE (Closing)', True),
        ]
        r = 3
        for entry in finbit_rows:
            if entry is None:
                ws.cell(r, 1, 'Derived Monthly Metrics').font = self.FONT_BOLD
                ws.row_dimensions[r].height = 18
                r += 1
                continue
            key, label, is_cur = entry
            ws.row_dimensions[r].height = 18
            ws.cell(r, 1, label).border = self.BORDER_THIN
            for ci, month_key in enumerate(finbit_months, 2):
                val = finbit_data[month_key].get(key, 0)
                ws.cell(r, ci, val).border = self.BORDER_THIN
                ws.cell(r, ci).number_format = self.FMT_CURRENCY if is_cur else self.FMT_INTEGER
            r += 1
        ws.column_dimensions['A'].width = 28
        for ci in range(2, len(finbit_months) + 2):
            ws.column_dimensions[get_column_letter(ci)].width = 18
        ws.freeze_panes = 'B3'
    
    def _build_summary(self, ws, metadata: Dict[str, Any]):
        """Build the Summary sheet matching the HDFC export structure."""
        ctx = self._ctx
        df = ctx["df"]
        months = ctx["months"]
        monthly = ctx["monthly"]

        def _month_label(m):
            return m.strftime("%b %Y")

        ws.column_dimensions['A'].width = 24
        ws.column_dimensions['B'].width = 22

        ws.cell(row=1, column=1, value='Name').font = self.FONT_BOLD
        ws.cell(row=1, column=1).border = self.BORDER_THIN
        ws.cell(row=1, column=2, value=metadata.get('full_name') or metadata.get('name') or '').border = self.BORDER_THIN
        ws.cell(row=2, column=1, value='Account No').font = self.FONT_BOLD
        ws.cell(row=2, column=1).border = self.BORDER_THIN
        ws.cell(row=2, column=2, value=metadata.get('account_no') or metadata.get('account_number') or '').border = self.BORDER_THIN
        ws.cell(row=3, column=1, value='Statement From').font = self.FONT_BOLD
        ws.cell(row=3, column=1).border = self.BORDER_THIN
        c = ws.cell(row=3, column=2, value=df['Date'].min().to_pydatetime() if len(df) else '')
        c.number_format = self.FMT_DATE
        c.border = self.BORDER_THIN
        ws.cell(row=4, column=1, value='Statement To').font = self.FONT_BOLD
        ws.cell(row=4, column=1).border = self.BORDER_THIN
        c = ws.cell(row=4, column=2, value=df['Date'].max().to_pydatetime() if len(df) else '')
        c.number_format = self.FMT_DATE
        c.border = self.BORDER_THIN

        for rno in [1, 2, 3, 4]:
            ws.row_dimensions[rno].height = 18

        ws.cell(row=6, column=1, value='').font = self.FONT_BOLD
        ws.cell(row=6, column=1).border = self.BORDER_THIN
        ws.cell(row=6, column=1).fill = self.FILL_HDFC_BLUE
        ws.cell(row=6, column=1).font = self.FONT_HEADER_WHITE
        ws.row_dimensions[6].height = 20
        for ci, m in enumerate(months, 2):
            cell = ws.cell(row=6, column=ci, value=_month_label(m))
            cell.font = self.FONT_HEADER_WHITE
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            cell.fill = self.FILL_HDFC_BLUE

        total_col = len(months) + 2
        ws.column_dimensions[get_column_letter(total_col)].width = 14
        total_header = ws.cell(row=6, column=total_col, value='Total/\nAverage')
        total_header.font = self.FONT_BOLD
        total_header.alignment = self.ALIGN_CENTER
        total_header.border = self.BORDER_THIN
        total_header.fill = self.FILL_HDFC_BLUE
        total_header.font = self.FONT_HEADER_WHITE

        row_labels = [
            ('Total Credit Count', 'credit_count', 'sum', self.FMT_INTEGER),
            ('Total Credit Amount', 'credit_amount', 'sum', self.FMT_CURRENCY),
            ('Total Debit Count', 'debit_count', 'sum', self.FMT_INTEGER),
            ('Total Debit Amount', 'debit_amount', 'sum', self.FMT_CURRENCY),
            ('Avg Balance', 'avg_balance', 'avg', self.FMT_CURRENCY),
            ('Min Balance', 'min_balance', 'min', self.FMT_CURRENCY),
            ('Max Balance', 'max_balance', 'max', self.FMT_CURRENCY),
            ('Start of Month Balance', 'start_balance', 'first', self.FMT_CURRENCY),
            ('End of Month Balance', 'end_balance', 'last', self.FMT_CURRENCY),
        ]

        for ri, (label, key, agg_type, fmt) in enumerate(row_labels, 7):
            ws.cell(row=ri, column=1, value=label).font = self.FONT_BOLD
            ws.cell(row=ri, column=1).border = self.BORDER_THIN
            ws.row_dimensions[ri].height = 18
            for ci, m in enumerate(months, 2):
                cell = ws.cell(row=ri, column=ci, value=monthly[m][key])
                cell.border = self.BORDER_THIN
                cell.number_format = fmt

            vals = [monthly[m][key] for m in months]
            total_cell = ws.cell(row=ri, column=total_col)
            if agg_type == 'sum':
                total_cell.value = sum(vals)
            elif agg_type == 'avg':
                total_cell.value = sum(vals) / len(vals) if vals else 0
            elif agg_type == 'min':
                total_cell.value = min(vals) if vals else 0
            elif agg_type == 'max':
                total_cell.value = max(vals) if vals else 0
            elif agg_type == 'first':
                total_cell.value = vals[0] if vals else 0
            elif agg_type == 'last':
                total_cell.value = vals[-1] if vals else 0
            total_cell.number_format = fmt
            total_cell.border = self.BORDER_THIN

        summary_row = 6 + len(row_labels) + 1
        cheque_counts = []
        top5_credit_amounts = []
        top5_credit_pcts = []
        top5_debit_amounts = []
        top5_debit_pcts = []
        bounce_counts = []
        salary_counts = []
        salary_amounts = []

        for m in months:
            mdf = df[df['Month'] == m]
            cheque_counts.append(len(mdf[mdf['IsCheque']]))
            crdf = mdf[mdf['Credit'] > 0]
            dbdf = mdf[mdf['Debit'] > 0]
            top5c = float(crdf.nlargest(5, 'Credit')['Credit'].sum()) if len(crdf) else 0.0
            top5d = float(dbdf.nlargest(5, 'Debit')['Debit'].sum()) if len(dbdf) else 0.0
            top5_credit_amounts.append(top5c)
            top5_debit_amounts.append(top5d)
            top5_credit_pcts.append(round((top5c / float(crdf['Credit'].sum()) * 100) if float(crdf['Credit'].sum()) > 0 else 0.0, 1))
            top5_debit_pcts.append(round((top5d / float(dbdf['Debit'].sum()) * 100) if float(dbdf['Debit'].sum()) > 0 else 0.0, 1))
            bounce_counts.append(len(mdf[mdf['Description'].str.lower().str.contains('cheque bounce|chq bounce|clg return|chq return', regex=True, na=False)]))
            salary_df = mdf[(mdf['Category'] == 'Salary') & (mdf['Credit'] > 0)]
            salary_counts.append(len(salary_df))
            salary_amounts.append(float(salary_df['Credit'].sum()))

        summary_items = [
            ('Total Cheque', cheque_counts, self.FMT_INTEGER),
            ('Top 5 credit amt', top5_credit_amounts, self.FMT_CURRENCY),
            ('Top 5 credit %', top5_credit_pcts, self.FMT_INTEGER),
            ('Top 5 debit amt', top5_debit_amounts, self.FMT_CURRENCY),
            ('top 5 debit %', top5_debit_pcts, self.FMT_INTEGER),
            ('cnt of cheque bounces', bounce_counts, self.FMT_INTEGER),
        ]

        is_salaried = (metadata.get('account_type', '') or '').lower() == 'salaried'
        if is_salaried:
            summary_items.extend([
                ('salary credit count', salary_counts, self.FMT_INTEGER),
                ('salary credit amt', salary_amounts, self.FMT_CURRENCY),
            ])

        summary_items.extend([
            ('Min EOD Balance', [monthly[m]['min_balance'] for m in months], self.FMT_CURRENCY),
            ('Max EOD Balance', [monthly[m]['max_balance'] for m in months], self.FMT_CURRENCY),
            ('Average EOD Balance', [monthly[m]['avg_balance'] for m in months], self.FMT_CURRENCY),
        ])
        for bd in [1, 5, 10, 15, 20, 25]:
            values = []
            for m in months:
                mdf = df[df['Month'] == m]
                if bd == 1:
                    values.append(self._first_day_balance(mdf, m))
                else:
                    day_txns = mdf[mdf['Date'].dt.day <= bd]
                    values.append(float(day_txns.iloc[-1]['Balance']) if len(day_txns) > 0 else 0.0)
            summary_items.append((f"Balance on {bd}{'st' if bd == 1 else 'th'}", values, self.FMT_CURRENCY))
        summary_items.append(('Balance on last day', [monthly[m]['end_balance'] for m in months], self.FMT_CURRENCY))

        current_row = summary_row
        for label, values, fmt in summary_items:
            ws.cell(row=current_row, column=1, value=label).font = self.FONT_BOLD
            ws.cell(row=current_row, column=1).border = self.BORDER_THIN
            ws.row_dimensions[current_row].height = 18
            for ci, value in enumerate(values, 2):
                cell = ws.cell(row=current_row, column=ci, value=value)
                cell.border = self.BORDER_THIN
                cell.number_format = fmt
            if values:
                total_value = sum(values) if fmt == self.FMT_CURRENCY or fmt == self.FMT_INTEGER else values[-1]
                if label.startswith('Min '):
                    total_value = min(values)
                elif label.startswith('Max '):
                    total_value = max(values)
                elif label == 'Average EOD Balance':
                    total_value = sum(values) / len(values)
                elif label in {'Top 5 credit %', 'top 5 debit %'}:
                    total_value = round(sum(values) / len(values), 1)
                elif label == 'Balance on last day':
                    total_value = values[-1] if values else 0
                cell = ws.cell(row=current_row, column=total_col, value=total_value)
                cell.border = self.BORDER_THIN
                cell.number_format = fmt
            current_row += 1

        ws.freeze_panes = 'B7'
    
    def _build_category_analysis(self, ws):
        """Build the Category Analysis sheet matching the HDFC report structure."""
        ctx = self._ctx
        df = ctx['df']
        months = ctx['months']
        monthly = ctx['monthly']
        monthly_weekly_credit = ctx['monthly_weekly_credit']
        monthly_weekly_debit = ctx['monthly_weekly_debit']

        credit_display = [
            ('UPI', {'UPI Transfer'}),
            ('Loan', {'Loan Disbursal'}),
            ('Salary Credits', {'Salary'}),
            ('Bank Transfer', {'Bank Transfer'}),
            ('Cash Deposit', {'Cash Deposit'}),
            ('Cheque Deposit', set()),
            ('Others', set()),
        ]
        debit_display = [
            ('Loan Payments', {'Loan Payment / EMI'}),
            ('ATM Withdrawal', {'ATM Withdrawal'}),
            ('Shopping', {'Shopping'}),
            ('Bill Payment', {'Bill Payment'}),
            ('Withdrawal', {'Transfer Out'}),
            ('Investments', {'Investment'}),
            ('Others', set()),
        ]

        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 16
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 3
        ws.column_dimensions['E'].width = 22
        ws.column_dimensions['F'].width = 16
        ws.column_dimensions['G'].width = 10

        ws.row_dimensions[1].height = 18
        ws.cell(1, 1, 'Credit Category').font = self.FONT_HEADER_WHITE
        ws.cell(1, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(1, 2, 'Amount').font = self.FONT_HEADER_WHITE
        ws.cell(1, 2).fill = self.FILL_HDFC_BLUE
        ws.cell(1, 3, 'Count').font = self.FONT_HEADER_WHITE
        ws.cell(1, 3).fill = self.FILL_HDFC_BLUE
        ws.cell(1, 5, 'Debit Category').font = self.FONT_HEADER_WHITE
        ws.cell(1, 5).fill = self.FILL_HDFC_BLUE
        ws.cell(1, 6, 'Amount').font = self.FONT_HEADER_WHITE
        ws.cell(1, 6).fill = self.FILL_HDFC_BLUE
        ws.cell(1, 7, 'Count').font = self.FONT_HEADER_WHITE
        ws.cell(1, 7).fill = self.FILL_HDFC_BLUE

        credit_known = set().union(*[aliases for label, aliases in credit_display if label not in {'Cheque Deposit', 'Others'}])
        debit_known = set().union(*[aliases for label, aliases in debit_display if label not in {'Others'}])

        cr_row = 2
        for label, aliases in credit_display:
            ws.row_dimensions[cr_row].height = 18
            ws.cell(cr_row, 1, label).border = self.BORDER_THIN
            if label == 'Cheque Deposit':
                cdf = df[(df['IsCheque']) & (df['Credit'] > 0)]
            elif label == 'Others':
                cdf = df[(df['Credit'] > 0) & (~df['Category'].isin(credit_known)) & (~df['IsCheque'])]
            else:
                cdf = df[(df['Category'].isin(aliases)) & (df['Credit'] > 0)]
            ws.cell(cr_row, 2, float(cdf['Credit'].sum())).border = self.BORDER_THIN
            ws.cell(cr_row, 2).number_format = self.FMT_CURRENCY
            ws.cell(cr_row, 3, len(cdf)).border = self.BORDER_THIN
            ws.cell(cr_row, 3).number_format = self.FMT_INTEGER
            cr_row += 1
        ws.row_dimensions[cr_row].height = 18
        ws.cell(cr_row, 1, 'Total').font = self.FONT_BOLD
        ws.cell(cr_row, 2, float(df[df['Credit'] > 0]['Credit'].sum())).border = self.BORDER_THIN
        ws.cell(cr_row, 3, int((df['Credit'] > 0).sum())).border = self.BORDER_THIN

        db_row = 2
        for label, aliases in debit_display:
            ws.row_dimensions[db_row].height = 18
            ws.cell(db_row, 5, label).border = self.BORDER_THIN
            if label == 'Others':
                ddf = df[(df['Debit'] > 0) & (~df['Category'].isin(debit_known))]
            else:
                ddf = df[(df['Category'].isin(aliases)) & (df['Debit'] > 0)]
            ws.cell(db_row, 6, float(ddf['Debit'].sum())).border = self.BORDER_THIN
            ws.cell(db_row, 6).number_format = self.FMT_CURRENCY
            ws.cell(db_row, 7, len(ddf)).border = self.BORDER_THIN
            ws.cell(db_row, 7).number_format = self.FMT_INTEGER
            db_row += 1
        ws.row_dimensions[db_row].height = 18
        ws.cell(db_row, 5, 'Total').font = self.FONT_BOLD
        ws.cell(db_row, 6, float(df[df['Debit'] > 0]['Debit'].sum())).border = self.BORDER_THIN
        ws.cell(db_row, 7, int((df['Debit'] > 0).sum())).border = self.BORDER_THIN

        tbl2_start = max(cr_row, db_row) + 3
        ws.row_dimensions[tbl2_start].height = 18
        for i, m in enumerate(months, 2):
            cell = ws.cell(tbl2_start, i, m.strftime('%b %Y'))
            cell.font = self.FONT_HEADER_WHITE
            cell.fill = self.FILL_HDFC_BLUE
            cell.border = self.BORDER_THIN
        ws.cell(tbl2_start, 1, 'Metric').font = self.FONT_HEADER_WHITE
        ws.cell(tbl2_start, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(tbl2_start, 1).border = self.BORDER_THIN
        labels2 = [
            'Total credit cnt', 'Total credit amt', 'Total debit cnt', 'Total debit amt',
            'Avg balance', 'Min balance', 'Max balance', 'Start of month bal', 'end of month bal',
        ]
        for r, label in enumerate(labels2, 1):
            ws.row_dimensions[tbl2_start + r].height = 18
            ws.cell(tbl2_start + r, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                m_data = monthly[m]
                value = (
                    m_data['credit_count'] if label == 'Total credit cnt' else
                    m_data['credit_amount'] if label == 'Total credit amt' else
                    m_data['debit_count'] if label == 'Total debit cnt' else
                    m_data['debit_amount'] if label == 'Total debit amt' else
                    m_data['avg_balance'] if label == 'Avg balance' else
                    m_data['min_balance'] if label == 'Min balance' else
                    m_data['max_balance'] if label == 'Max balance' else
                    m_data['start_balance'] if label == 'Start of month bal' else
                    m_data['end_balance']
                )
                cell = ws.cell(tbl2_start + r, i, value)
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_INTEGER if 'cnt' in label else self.FMT_CURRENCY

        tbl3_start = tbl2_start + 1 + len(labels2) + 2
        ws.row_dimensions[tbl3_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(tbl3_start, i * 2 - 1, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl3_start, i * 2 - 1).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl3_start, i * 2 - 1).border = self.BORDER_THIN
            ws.cell(tbl3_start, i * 2, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl3_start, i * 2).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl3_start, i * 2).border = self.BORDER_THIN
        ws.row_dimensions[tbl3_start + 1].height = 18
        ws.cell(tbl3_start + 1, 1, 'Credit Category').font = self.FONT_HEADER_WHITE
        ws.cell(tbl3_start + 1, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(tbl3_start + 1, 1).border = self.BORDER_THIN
        cr_row_m = tbl3_start + 2
        for label, aliases in credit_display:
            ws.row_dimensions[cr_row_m].height = 18
            ws.cell(cr_row_m, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                if label == 'Cheque Deposit':
                    mdf = df[(df['Month'] == m) & (df['IsCheque']) & (df['Credit'] > 0)]
                elif label == 'Others':
                    mdf = df[(df['Month'] == m) & (df['Credit'] > 0) & (~df['Category'].isin(credit_known)) & (~df['IsCheque'])]
                else:
                    mdf = df[(df['Month'] == m) & (df['Category'].isin(aliases)) & (df['Credit'] > 0)]
                ws.cell(cr_row_m, i * 2 - 1, float(mdf['Credit'].sum())).number_format = self.FMT_CURRENCY
                ws.cell(cr_row_m, i * 2, len(mdf)).number_format = self.FMT_INTEGER
            cr_row_m += 1
        ws.row_dimensions[cr_row_m].height = 18
        ws.cell(cr_row_m, 1, 'Total credit amt').font = self.FONT_BOLD
        for i, m in enumerate(months, 2):
            ws.cell(cr_row_m, i * 2 - 1, monthly[m]['credit_amount']).number_format = self.FMT_CURRENCY
            ws.cell(cr_row_m, i * 2, monthly[m]['credit_count']).number_format = self.FMT_INTEGER

        tbl4_start = cr_row_m + 3
        ws.row_dimensions[tbl4_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(tbl4_start, i * 2 - 1, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl4_start, i * 2 - 1).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl4_start, i * 2 - 1).border = self.BORDER_THIN
            ws.cell(tbl4_start, i * 2, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl4_start, i * 2).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl4_start, i * 2).border = self.BORDER_THIN
        ws.row_dimensions[tbl4_start + 1].height = 18
        ws.cell(tbl4_start + 1, 1, 'Debit Categories').font = self.FONT_HEADER_WHITE
        ws.cell(tbl4_start + 1, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(tbl4_start + 1, 1).border = self.BORDER_THIN
        db_row_m = tbl4_start + 2
        for label, aliases in debit_display:
            ws.row_dimensions[db_row_m].height = 18
            ws.cell(db_row_m, 1, label).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                if label == 'Others':
                    mdf = df[(df['Month'] == m) & (df['Debit'] > 0) & (~df['Category'].isin(debit_known))]
                else:
                    mdf = df[(df['Month'] == m) & (df['Category'].isin(aliases)) & (df['Debit'] > 0)]
                ws.cell(db_row_m, i * 2 - 1, float(mdf['Debit'].sum())).number_format = self.FMT_CURRENCY
                ws.cell(db_row_m, i * 2, len(mdf)).number_format = self.FMT_INTEGER
            db_row_m += 1
        ws.row_dimensions[db_row_m].height = 18
        ws.cell(db_row_m, 1, 'Total debit amt').font = self.FONT_BOLD
        for i, m in enumerate(months, 2):
            ws.cell(db_row_m, i * 2 - 1, monthly[m]['debit_amount']).number_format = self.FMT_CURRENCY
            ws.cell(db_row_m, i * 2, monthly[m]['debit_count']).number_format = self.FMT_INTEGER

        tbl5_start = db_row_m + 3
        ws.row_dimensions[tbl5_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(tbl5_start, i, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl5_start, i).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl5_start, i).border = self.BORDER_THIN
        ws.cell(tbl5_start, 1, 'Week').font = self.FONT_HEADER_WHITE
        ws.cell(tbl5_start, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(tbl5_start, 1).border = self.BORDER_THIN
        wr = tbl5_start + 1
        for w in ["Week 1 (1-5)", "Week 2 (6-10)", "Week 3 (11-15)", "Week 4 (16-20)", "Week 5 (21-25)", "Week 6 (26-end)"]:
            ws.row_dimensions[wr].height = 18
            ws.cell(wr, 1, w).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                ws.cell(wr, i, monthly_weekly_credit[m][w]['amount']).number_format = self.FMT_CURRENCY
            wr += 1
        ws.row_dimensions[wr].height = 18
        ws.cell(wr, 1, 'Total credit amt').font = self.FONT_BOLD
        for i, m in enumerate(months, 2):
            ws.cell(wr, i, monthly[m]['credit_amount']).number_format = self.FMT_CURRENCY

        right_wk_start = 5
        ws.row_dimensions[tbl5_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(tbl5_start, right_wk_start + i - 1, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(tbl5_start, right_wk_start + i - 1).fill = self.FILL_HDFC_BLUE
            ws.cell(tbl5_start, right_wk_start + i - 1).border = self.BORDER_THIN
        ws.cell(tbl5_start, right_wk_start, 'Week').font = self.FONT_HEADER_WHITE
        ws.cell(tbl5_start, right_wk_start).fill = self.FILL_HDFC_BLUE
        ws.cell(tbl5_start, right_wk_start).border = self.BORDER_THIN
        wr2 = tbl5_start + 1
        for w in ["Week 1 (1-5)", "Week 2 (6-10)", "Week 3 (11-15)", "Week 4 (16-20)", "Week 5 (21-25)", "Week 6 (26-end)"]:
            ws.row_dimensions[wr2].height = 18
            ws.cell(wr2, right_wk_start, w).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                ws.cell(wr2, right_wk_start + i - 1, monthly_weekly_debit[m][w]['amount']).number_format = self.FMT_CURRENCY
            wr2 += 1
        ws.row_dimensions[wr2].height = 18
        ws.cell(wr2, right_wk_start, 'Total debit amt').font = self.FONT_BOLD
        for i, m in enumerate(months, 2):
            ws.cell(wr2, right_wk_start + i - 1, monthly[m]['debit_amount']).number_format = self.FMT_CURRENCY
    
    def _build_weekly_analysis(self, ws):
        """Build the Weekly Analysis sheet matching the HDFC report structure."""
        ctx = self._ctx
        months = ctx['months']
        weekly_credit = ctx['weekly_credit']
        weekly_debit = ctx['weekly_debit']
        monthly_weekly_credit = ctx['monthly_weekly_credit']
        monthly_weekly_debit = ctx['monthly_weekly_debit']
        week_order = ["Week 1 (1-5)", "Week 2 (6-10)", "Week 3 (11-15)", "Week 4 (16-20)", "Week 5 (21-25)", "Week 6 (26-end)"]

        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 14
        ws.column_dimensions['D'].width = 3
        ws.column_dimensions['E'].width = 22
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 14

        ws.row_dimensions[1].height = 18
        for ci, h in enumerate(['Week', 'Credit Amount', 'Credit Count'], 1):
            c = ws.cell(1, ci, h)
            c.font = self.FONT_HEADER_WHITE
            c.fill = self.FILL_HDFC_BLUE
            c.border = self.BORDER_THIN
        for ci, h in enumerate(['Week', 'Debit Amount', 'Debit Count'], 5):
            c = ws.cell(1, ci, h)
            c.font = self.FONT_HEADER_WHITE
            c.fill = self.FILL_HDFC_BLUE
            c.border = self.BORDER_THIN

        total_row = len(week_order) + 2
        for ri, w in enumerate(week_order, 2):
            ws.row_dimensions[ri].height = 18
            ws.cell(ri, 1, w).border = self.BORDER_THIN
            ws.cell(ri, 2, weekly_credit[w]['amount']).border = self.BORDER_THIN
            ws.cell(ri, 2).number_format = self.FMT_CURRENCY
            ws.cell(ri, 3, weekly_credit[w]['count']).border = self.BORDER_THIN
            ws.cell(ri, 3).number_format = self.FMT_INTEGER
            ws.cell(ri, 5, w).border = self.BORDER_THIN
            ws.cell(ri, 6, weekly_debit[w]['amount']).border = self.BORDER_THIN
            ws.cell(ri, 6).number_format = self.FMT_CURRENCY
            ws.cell(ri, 7, weekly_debit[w]['count']).border = self.BORDER_THIN
            ws.cell(ri, 7).number_format = self.FMT_INTEGER

        ws.row_dimensions[total_row].height = 18
        ws.cell(total_row, 1, 'Total').font = self.FONT_BOLD
        ws.cell(total_row, 2, sum(weekly_credit[w]['amount'] for w in week_order)).border = self.BORDER_THIN
        ws.cell(total_row, 2).number_format = self.FMT_CURRENCY
        ws.cell(total_row, 3, sum(weekly_credit[w]['count'] for w in week_order)).border = self.BORDER_THIN
        ws.cell(total_row, 3).number_format = self.FMT_INTEGER
        ws.cell(total_row, 5, 'Total').font = self.FONT_BOLD
        ws.cell(total_row, 6, sum(weekly_debit[w]['amount'] for w in week_order)).border = self.BORDER_THIN
        ws.cell(total_row, 6).number_format = self.FMT_CURRENCY
        ws.cell(total_row, 7, sum(weekly_debit[w]['count'] for w in week_order)).border = self.BORDER_THIN
        ws.cell(total_row, 7).number_format = self.FMT_INTEGER

        mom_start = total_row + 3
        ws.row_dimensions[mom_start].height = 18
        self._style_section_header(ws, mom_start, 1, 7, 'MONTH OVER MONTH — WEEKLY CREDIT')
        mom_start += 1
        ws.row_dimensions[mom_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(mom_start, i, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(mom_start, i).fill = self.FILL_HDFC_BLUE
            ws.cell(mom_start, i).border = self.BORDER_THIN
        ws.cell(mom_start, 1, 'Week').font = self.FONT_HEADER_WHITE
        ws.cell(mom_start, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(mom_start, 1).border = self.BORDER_THIN
        for w_row, w in enumerate(week_order, mom_start + 1):
            ws.row_dimensions[w_row].height = 18
            ws.cell(w_row, 1, w).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                cell = ws.cell(w_row, i, monthly_weekly_credit[m][w]['amount'])
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_CURRENCY
        change_row = mom_start + 1 + len(week_order)
        ws.row_dimensions[change_row].height = 18
        ws.cell(change_row, 1, 'MoM Credit Change').border = self.BORDER_THIN
        ws.row_dimensions[change_row + 1].height = 18
        ws.cell(change_row + 1, 1, 'MoM Credit %').border = self.BORDER_THIN
        prev = None
        for i, m in enumerate(months, 2):
            cur = sum(monthly_weekly_credit[m][w]['amount'] for w in week_order)
            ch = 0.0 if prev is None else cur - prev
            pc = 0.0 if prev in (None, 0) else (ch / prev * 100)
            # MoM Credit Change - green for positive, red for negative
            c = ws.cell(change_row, i, ch)
            c.border = self.BORDER_THIN
            c.number_format = self.FMT_CURRENCY
            if ch > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif ch < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            # MoM Credit % - green for positive, red for negative
            c = ws.cell(change_row + 1, i, pc)
            c.border = self.BORDER_THIN
            c.number_format = '0.0%'
            if pc > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif pc < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            prev = cur

        debit_start = change_row + 3
        ws.row_dimensions[debit_start].height = 18
        self._style_section_header(ws, debit_start, 1, 7, 'MONTH OVER MONTH — WEEKLY DEBIT')
        debit_start += 1
        ws.row_dimensions[debit_start].height = 18
        for i, m in enumerate(months, 2):
            ws.cell(debit_start, i, m.strftime('%b %Y')).font = self.FONT_HEADER_WHITE
            ws.cell(debit_start, i).fill = self.FILL_HDFC_BLUE
            ws.cell(debit_start, i).border = self.BORDER_THIN
        ws.cell(debit_start, 1, 'Week').font = self.FONT_HEADER_WHITE
        ws.cell(debit_start, 1).fill = self.FILL_HDFC_BLUE
        ws.cell(debit_start, 1).border = self.BORDER_THIN
        for w_row, w in enumerate(week_order, debit_start + 1):
            ws.row_dimensions[w_row].height = 18
            ws.cell(w_row, 1, w).border = self.BORDER_THIN
            for i, m in enumerate(months, 2):
                cell = ws.cell(w_row, i, monthly_weekly_debit[m][w]['amount'])
                cell.border = self.BORDER_THIN
                cell.number_format = self.FMT_CURRENCY
        dchange_row = debit_start + 1 + len(week_order)
        ws.row_dimensions[dchange_row].height = 18
        ws.cell(dchange_row, 1, 'MoM Debit Change').border = self.BORDER_THIN
        ws.row_dimensions[dchange_row + 1].height = 18
        ws.cell(dchange_row + 1, 1, 'MoM Debit %').border = self.BORDER_THIN
        prev = None
        for i, m in enumerate(months, 2):
            cur = sum(monthly_weekly_debit[m][w]['amount'] for w in week_order)
            ch = 0.0 if prev is None else cur - prev
            pc = 0.0 if prev in (None, 0) else (ch / prev * 100)
            # MoM Debit Change - green for positive, red for negative
            c = ws.cell(dchange_row, i, ch)
            c.border = self.BORDER_THIN
            c.number_format = self.FMT_CURRENCY
            if ch > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif ch < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            # MoM Debit % - green for positive, red for negative
            c = ws.cell(dchange_row + 1, i, pc)
            c.border = self.BORDER_THIN
            c.number_format = '0.0%'
            if pc > 0:
                c.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif pc < 0:
                c.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            prev = cur
    
    def _build_recurring_analysis(self, ws):
        """Build the Recurring Analysis sheet."""
        lr = self.last_row
        RAW = f"'{self.RAW_SHEET}'"
        
        # ═══════════════════════════════════════════════════
        # LEFT TABLE - Credit Recurring (Column A-C)
        # ═══════════════════════════════════════════════════
        
        # Header row
        headers_left = ['Type', 'Credit Amount', 'Credit Count']
        for col, header in enumerate(headers_left, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.FONT_BOLD
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            cell.fill = self.FILL_LIGHT_BLUE
        
        # Recurring types
        recurring_types = [
            ('Recurring', 'Yes'),
            ('Non-Recurring', 'No'),
            ('Total', None)
        ]
        
        for row_offset, (label, flag) in enumerate(recurring_types):
            row_idx = 2 + row_offset
            
            # Type label
            cell = ws.cell(row=row_idx, column=1, value=label)
            cell.font = self.FONT_BOLD if label == 'Total' else self.FONT_DEFAULT
            cell.alignment = self.ALIGN_LEFT
            cell.border = self.BORDER_THIN
            
            if label == 'Total':
                # Sum of above
                amount_formula = '=SUM(B2:B3)'
                count_formula = '=SUM(C2:C3)'
            else:
                # SUMIFS/COUNTIFS formula
                amount_formula = f'=SUMIFS({RAW}!D$2:D${lr},{RAW}!H$2:H${lr},"{flag}")'
                count_formula = f'=COUNTIFS({RAW}!H$2:H${lr},"{flag}",{RAW}!D$2:D${lr},">"&0)'
            
            # Amount
            cell = ws.cell(row=row_idx, column=2, value=amount_formula)
            cell.number_format = self.FMT_CURRENCY
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            
            # Count
            cell = ws.cell(row=row_idx, column=3, value=count_formula)
            cell.number_format = self.FMT_INTEGER
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
        
        # ═══════════════════════════════════════════════════
        # RIGHT TABLE - Debit Recurring (Column F-H)
        # ═══════════════════════════════════════════════════
        
        # Header row
        headers_right = ['Type', 'Debit Amount', 'Debit Count']
        for col_offset, header in enumerate(headers_right):
            col = 6 + col_offset
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.FONT_BOLD
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            cell.fill = self.FILL_LIGHT_ORANGE
        
        for row_offset, (label, flag) in enumerate(recurring_types):
            row_idx = 2 + row_offset
            
            # Type label
            cell = ws.cell(row=row_idx, column=6, value=label)
            cell.font = self.FONT_BOLD if label == 'Total' else self.FONT_DEFAULT
            cell.alignment = self.ALIGN_LEFT
            cell.border = self.BORDER_THIN
            
            if label == 'Total':
                # Sum of above
                amount_formula = '=SUM(G2:G3)'
                count_formula = '=SUM(H2:H3)'
            else:
                # SUMIFS/COUNTIFS formula
                amount_formula = f'=SUMIFS({RAW}!C$2:C${lr},{RAW}!H$2:H${lr},"{flag}")'
                count_formula = f'=COUNTIFS({RAW}!H$2:H${lr},"{flag}",{RAW}!C$2:C${lr},">"&0)'
            
            # Amount
            cell = ws.cell(row=row_idx, column=7, value=amount_formula)
            cell.number_format = self.FMT_CURRENCY
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
            
            # Count
            cell = ws.cell(row=row_idx, column=8, value=count_formula)
            cell.number_format = self.FMT_INTEGER
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.BORDER_THIN
        
        # Column widths
        ws.column_dimensions['A'].width = 18
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 14
        ws.column_dimensions['E'].width = 3  # Spacer
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 18
        ws.column_dimensions['H'].width = 14
