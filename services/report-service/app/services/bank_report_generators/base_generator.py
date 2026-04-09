"""
Base report generator class for all bank report generators.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from ...utils.logging import get_logger

logger = get_logger(__name__)

class BaseBankReportGenerator(ABC):
    """Base class for bank-specific report generators."""
    
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
    
    @abstractmethod
    async def generate_sheets(
        self, 
        workbook: Workbook, 
        transactions: List[Dict[str, Any]], 
        user_info: Dict[str, Any],
        ai_results: Optional[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[str]:
        """
        Generate Excel sheets for the bank report.
        
        Args:
            workbook: Excel workbook object
            transactions: List of transactions
            user_info: User information
            ai_results: AI analysis results
            options: Report generation options
            
        Returns:
            List of sheet names created
        """
        pass
    
    def _create_transactions_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create standard transactions sheet."""
        ws = workbook.create_sheet("Transactions")
        
        # Headers
        headers = ["Date", "Description", "Amount", "Type", "Balance", "Category", "Subcategory", "Confidence"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        # Data
        for row, txn in enumerate(transactions, 2):
            ws.cell(row=row, column=1, value=txn.get('date', ''))
            ws.cell(row=row, column=2, value=txn.get('description', ''))
            ws.cell(row=row, column=3, value=txn.get('amount', 0))
            ws.cell(row=row, column=4, value=txn.get('type', ''))
            ws.cell(row=row, column=5, value=txn.get('balance', ''))
            ws.cell(row=row, column=6, value=txn.get('category', ''))
            ws.cell(row=row, column=7, value=txn.get('subcategory', ''))
            ws.cell(row=row, column=8, value=txn.get('confidence', ''))
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        return "Transactions"
    
    def _create_summary_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create summary sheet."""
        ws = workbook.create_sheet("Summary")
        
        # Basic statistics
        total_transactions = len(transactions)
        credits = [t for t in transactions if t.get('type', '').lower() == 'credit']
        debits = [t for t in transactions if t.get('type', '').lower() == 'debit']
        total_amount = sum(t.get('amount', 0) for t in transactions)
        
        # Write summary data
        summary_data = [
            ["Metric", "Value"],
            ["Total Transactions", total_transactions],
            ["Total Credits", len(credits)],
            ["Total Debits", len(debits)],
            ["Total Amount", total_amount],
            ["Average Transaction", total_amount / total_transactions if total_transactions > 0 else 0]
        ]
        
        for row, (label, value) in enumerate(summary_data, 1):
            ws.cell(row=row, column=1, value=label)
            ws.cell(row=row, column=2, value=value)
            
            if row == 1:
                ws.cell(row=row, column=1).font = Font(bold=True)
                ws.cell(row=row, column=2).font = Font(bold=True)
                ws.cell(row=row, column=1).fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
                ws.cell(row=row, column=2).fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20
        
        return "Summary"
    
    def _create_category_analysis_sheet(self, workbook: Workbook, transactions: List[Dict[str, Any]]) -> str:
        """Create category analysis sheet."""
        ws = workbook.create_sheet("Category Analysis")
        
        # Count transactions by category
        categories = {}
        category_amounts = {}
        
        for txn in transactions:
            cat = txn.get('category', 'Uncategorized')
            amount = txn.get('amount', 0)
            
            categories[cat] = categories.get(cat, 0) + 1
            category_amounts[cat] = category_amounts.get(cat, 0) + amount
        
        # Headers
        headers = ["Category", "Transaction Count", "Total Amount", "Average Amount"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        # Data
        for row, (category, count) in enumerate(categories.items(), 2):
            total_amount = category_amounts[category]
            avg_amount = total_amount / count if count > 0 else 0
            
            ws.cell(row=row, column=1, value=category)
            ws.cell(row=row, column=2, value=count)
            ws.cell(row=row, column=3, value=total_amount)
            ws.cell(row=row, column=4, value=avg_amount)
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        return "Category Analysis"
    
    def _apply_bank_styling(self, worksheet, bank_name: str):
        """Apply bank-specific styling to worksheet."""
        # This can be overridden by bank-specific generators
        pass
    
    def _get_bank_color_scheme(self) -> Dict[str, str]:
        """Get bank-specific color scheme."""
        # Default color scheme, can be overridden
        return {
            "primary": "2E75B6",
            "secondary": "A9D18E",
            "accent": "FFC000",
            "header": "DDDDDD"
        }
