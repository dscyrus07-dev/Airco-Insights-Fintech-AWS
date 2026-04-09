"""
Base processor class for all bank processors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ...utils.logging import get_logger

logger = get_logger(__name__)

class BaseBankProcessor(ABC):
    """Base class for bank-specific PDF processors."""
    
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
    
    @abstractmethod
    async def process_pdf(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PDF file and extract transactions.
        
        Args:
            file_path: Path to PDF file
            options: Processing options
            
        Returns:
            Dictionary containing:
            - transactions: List of transaction dictionaries
            - metadata: Processing metadata
            - errors: List of processing errors
        """
        pass
    
    @abstractmethod
    def validate_pdf(self, file_path: str) -> bool:
        """
        Validate if PDF is from this bank.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if PDF is from this bank, False otherwise
        """
        pass
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to standard format."""
        # Implement date normalization logic
        return date_str
    
    def _normalize_amount(self, amount_str: str) -> float:
        """Normalize amount string to float."""
        # Remove common currency symbols and formatting
        import re
        cleaned = re.sub(r'[^\d.-]', '', str(amount_str))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _determine_transaction_type(self, description: str, amount: float) -> str:
        """Determine if transaction is credit or debit based on description and amount."""
        # Implement logic to determine transaction type
        # This can be customized per bank
        description_lower = description.lower()
        
        # Common credit indicators
        credit_keywords = ['credit', 'deposit', 'received', 'salary', 'refund', 'interest']
        
        # Common debit indicators
        debit_keywords = ['debit', 'withdrawal', 'payment', 'transfer', 'purchase', 'atm']
        
        for keyword in credit_keywords:
            if keyword in description_lower:
                return 'credit'
        
        for keyword in debit_keywords:
            if keyword in description_lower:
                return 'debit'
        
        # If amount is positive, assume credit, otherwise debit
        return 'credit' if amount >= 0 else 'debit'
