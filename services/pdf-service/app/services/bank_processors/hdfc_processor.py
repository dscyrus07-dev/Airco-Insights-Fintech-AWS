"""
HDFC Bank PDF processor implementation.
"""

import pdfplumber
from typing import Dict, Any, List
from .base_processor import BaseBankProcessor
from ...utils.logging import get_logger

logger = get_logger(__name__)

class HDFCProcessor(BaseBankProcessor):
    """HDFC Bank statement processor."""
    
    def __init__(self):
        super().__init__("hdfc")
    
    async def process_pdf(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process HDFC PDF statement."""
        transactions = []
        errors = []
        metadata = {
            'bank': 'hdfc',
            'processor_version': '1.0.0'
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if not text:
                            continue
                        
                        # Extract transactions from page text
                        page_transactions = self._extract_transactions_from_text(text, page_num + 1)
                        transactions.extend(page_transactions)
                        
                    except Exception as e:
                        error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Error opening PDF file: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        logger.info("HDFC PDF processing completed", 
                   transaction_count=len(transactions),
                   errors=len(errors))
        
        return {
            'transactions': transactions,
            'metadata': metadata,
            'errors': errors
        }
    
    def validate_pdf(self, file_path: str) -> bool:
        """Validate if PDF is from HDFC."""
        try:
            with pdfplumber.open(file_path) as pdf:
                # Check first few pages for HDFC indicators
                for page in pdf.pages[:3]:
                    text = page.extract_text()
                    if text and ('hdfc' in text.lower() or 'hdfc bank' in text.lower()):
                        return True
            return False
        except:
            return False
    
    def _extract_transactions_from_text(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Extract transactions from page text."""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or self._is_header_line(line):
                continue
            
            # Try to parse transaction line
            transaction = self._parse_transaction_line(line)
            if transaction:
                transaction['page_number'] = page_num
                transactions.append(transaction)
        
        return transactions
    
    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header/footer line."""
        header_indicators = [
            'date', 'description', 'amount', 'balance',
            'transaction', 'account', 'statement',
            'page', 'hdfc bank', 'continued'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in header_indicators)
    
    def _parse_transaction_line(self, line: str) -> Dict[str, Any]:
        """Parse a single transaction line."""
        # HDFC transaction format typically:
        # Date Description Amount Balance
        
        parts = line.split()
        if len(parts) < 3:
            return None
        
        # Try to extract date (first part)
        date_part = parts[0]
        if not self._is_valid_date(date_part):
            return None
        
        # Extract amount (usually last numeric part)
        amount = 0.0
        balance = 0.0
        
        # Find numeric values in the line
        import re
        numbers = re.findall(r'[\d,]+\.?\d*', line)
        
        if len(numbers) >= 2:
            # Last number is likely balance, second last is amount
            try:
                balance = self._normalize_amount(numbers[-1])
                amount = self._normalize_amount(numbers[-2])
            except ValueError:
                pass
        elif len(numbers) == 1:
            try:
                amount = self._normalize_amount(numbers[0])
            except ValueError:
                pass
        
        # Extract description (everything between date and amounts)
        description_parts = parts[1:-2] if len(parts) > 3 else parts[1:-1]
        description = ' '.join(description_parts)
        
        # Determine transaction type
        txn_type = self._determine_transaction_type(description, amount)
        
        return {
            'date': self._normalize_date(date_part),
            'description': description,
            'amount': amount,
            'type': txn_type,
            'balance': balance,
            'raw_line': line
        }
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string is a valid date format."""
        import re
        # Check for common date formats: DD-MM-YY, DD/MM/YY, etc.
        date_pattern = r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$'
        return bool(re.match(date_pattern, date_str))
