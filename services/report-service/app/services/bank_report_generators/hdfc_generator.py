"""
HDFC Bank report generator implementation.
"""

from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)

class HDFCReportGenerator(BaseBankReportGenerator):
    """HDFC Bank report generator."""
    
    def __init__(self):
        super().__init__("hdfc")
    
    async def generate_sheets(
        self, 
        workbook: Workbook, 
        transactions: List[Dict[str, Any]], 
        user_info: Dict[str, Any],
        ai_results: Optional[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[str]:
        """Generate HDFC-specific Excel sheets."""
        sheets_created = []
        
        # Create standard sheets
        sheets_created.append(self._create_transactions_sheet(workbook, transactions))
        sheets_created.append(self._create_summary_sheet(workbook, transactions))
        sheets_created.append(self._create_category_analysis_sheet(workbook, transactions))
        
        # Create HDFC-specific sheets
        sheets_created.append(self._create_hdfc_monthly_trends_sheet(workbook, transactions))
        sheets_created.append(self._create_hdfc_source_analysis_sheet(workbook, transactions))
        sheets_created.append(self._create_hdfc_category_outcome_sheet(workbook, transactions))
        
        # Apply HDFC styling
        for sheet_name in sheets_created:
            if sheet_name in workbook.sheetnames:
                self._apply_hdfc_styling(workbook[sheet_name])
        
        logger.info("HDFC report sheets generated", sheets=sheets_created)
        return sheets_created
    
    def _create_hdfc_monthly_trends_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create HDFC monthly trends analysis sheet."""
        ws = workbook.create_sheet("Monthly Trends")
        
        # Group transactions by month
        monthly_data = {}
        for txn in transactions:
            date = txn.get('date', '')
            if date and len(date) >= 7:
                month = date[:7]  # YYYY-MM format
                if month not in monthly_data:
                    monthly_data[month] = {'credits': 0, 'debits': 0, 'count': 0}
                
                amount = txn.get('amount', 0)
                txn_type = txn.get('type', '').lower()
                
                monthly_data[month]['count'] += 1
                if txn_type == 'credit':
                    monthly_data[month]['credits'] += amount
                else:
                    monthly_data[month]['debits'] += amount
        
        # Headers
        headers = ["Month", "Transactions", "Total Credits", "Total Debits", "Net Flow"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
            cell.font = Font(color="FFFFFF", bold=True)
        
        # Data
        for row, (month, data) in enumerate(sorted(monthly_data.items()), 2):
            net_flow = data['credits'] - data['debits']
            
            ws.cell(row=row, column=1, value=month)
            ws.cell(row=row, column=2, value=data['count'])
            ws.cell(row=row, column=3, value=data['credits'])
            ws.cell(row=row, column=4, value=data['debits'])
            ws.cell(row=row, column=5, value=net_flow)
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
        return "Monthly Trends"
    
    def _create_hdfc_source_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create HDFC source analysis sheet (Sheet 9)."""
        ws = workbook.create_sheet("Source Analysis")
        
        # Analyze transaction sources/descriptions
        source_patterns = {}
        
        for txn in transactions:
            description = txn.get('description', '').lower()
            amount = txn.get('amount', 0)
            
            # Extract common patterns
            if 'upi' in description:
                pattern = 'UPI'
            elif 'atm' in description:
                pattern = 'ATM'
            elif 'neft' in description or 'rtgs' in description:
                pattern = 'NEFT/RTGS'
            elif 'imps' in description:
                pattern = 'IMPS'
            elif 'cheque' in description:
                pattern = 'Cheque'
            else:
                pattern = 'Other'
            
            if pattern not in source_patterns:
                source_patterns[pattern] = {'count': 0, 'total_amount': 0}
            
            source_patterns[pattern]['count'] += 1
            source_patterns[pattern]['total_amount'] += amount
        
        # Headers
        headers = ["Source Type", "Transaction Count", "Total Amount", "Average Amount", "% of Total"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")
            cell.font = Font(color="FFFFFF", bold=True)
        
        # Calculate total amount for percentage
        total_amount = sum(data['total_amount'] for data in source_patterns.values())
        
        # Data
        for row, (pattern, data) in enumerate(sorted(source_patterns.items(), key=lambda x: x[1]['total_amount'], reverse=True), 2):
            avg_amount = data['total_amount'] / data['count'] if data['count'] > 0 else 0
            percentage = (data['total_amount'] / total_amount * 100) if total_amount > 0 else 0
            
            ws.cell(row=row, column=1, value=pattern)
            ws.cell(row=row, column=2, value=data['count'])
            ws.cell(row=row, column=3, value=data['total_amount'])
            ws.cell(row=row, column=4, value=avg_amount)
            ws.cell(row=row, column=5, value=f"{percentage:.2f}%")
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        return "Source Analysis"
    
    def _create_hdfc_category_outcome_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create HDFC category outcome sheet (Sheet 10)."""
        ws = workbook.create_sheet("Category Outcome")
        
        # Analyze category outcomes
        category_outcomes = {}
        
        for txn in transactions:
            category = txn.get('category', 'Uncategorized')
            amount = txn.get('amount', 0)
            txn_type = txn.get('type', '').lower()
            
            if category not in category_outcomes:
                category_outcomes[category] = {
                    'credits': 0, 'debits': 0, 'count': 0, 'net': 0
                }
            
            category_outcomes[category]['count'] += 1
            if txn_type == 'credit':
                category_outcomes[category]['credits'] += amount
            else:
                category_outcomes[category]['debits'] += amount
            
            category_outcomes[category]['net'] = (
                category_outcomes[category]['credits'] - 
                category_outcomes[category]['debits']
            )
        
        # Headers
        headers = ["Category", "Transactions", "Credits", "Debits", "Net Outcome", "Trend"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
            cell.font = Font(color="FFFFFF", bold=True)
        
        # Data
        for row, (category, data) in enumerate(sorted(category_outcomes.items(), key=lambda x: x[1]['net'], reverse=True), 2):
            trend = "Positive" if data['net'] > 0 else "Negative" if data['net'] < 0 else "Neutral"
            
            ws.cell(row=row, column=1, value=category)
            ws.cell(row=row, column=2, value=data['count'])
            ws.cell(row=row, column=3, value=data['credits'])
            ws.cell(row=row, column=4, value=data['debits'])
            ws.cell(row=row, column=5, value=data['net'])
            ws.cell(row=row, column=6, value=trend)
            
            # Apply conditional formatting for trend
            if trend == "Positive":
                ws.cell(row=row, column=6).fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
            elif trend == "Negative":
                ws.cell(row=row, column=6).fill = PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid")
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
        return "Category Outcome"
    
    def _apply_hdfc_styling(self, worksheet):
        """Apply HDFC-specific styling."""
        # HDFC color scheme
        hdfc_colors = {
            "primary": "2E75B6",  # HDFC blue
            "secondary": "A9D18E",  # Green
            "accent": "FFC000",  # Gold
            "header": "DDDDDD"
        }
        
        # Apply styling to header row if exists
        if worksheet.max_row >= 1:
            for col in range(1, worksheet.max_column + 1):
                cell = worksheet.cell(row=1, column=col)
                if cell.fill.start_color.rgb == "FFFFFFFF":  # If white, make it HDFC blue
                    cell.fill = PatternFill(start_color=hdfc_colors["primary"], end_color=hdfc_colors["primary"], fill_type="solid")
                    cell.font = Font(color="FFFFFF", bold=True)
    
    def _get_bank_color_scheme(self) -> Dict[str, str]:
        """Get HDFC-specific color scheme."""
        return {
            "primary": "2E75B6",  # HDFC blue
            "secondary": "A9D18E",  # Green
            "accent": "FFC000",  # Gold
            "header": "DDDDDD"
        }
