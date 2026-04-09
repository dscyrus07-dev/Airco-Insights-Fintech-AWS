"""
Bank processor factory for creating bank-specific processors.
"""

from typing import Dict, List
from .hdfc_processor import HDFCProcessor
from .base_processor import BaseBankProcessor
from ...utils.logging import get_logger

logger = get_logger(__name__)


class AxisProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("axis")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "axis"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class ICICIProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("icici")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "icici"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class KotakProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("kotak")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "kotak"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class SBIProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("sbi")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "sbi"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False

class BankProcessorFactory:
    """Factory for creating bank-specific processors."""
    
    def __init__(self):
        self._processors: Dict[str, object] = {
            'hdfc': HDFCProcessor(),
            'axis': AxisProcessor(),
            'icici': ICICIProcessor(),
            'kotak': KotakProcessor(),
            'sbi': SBIProcessor()
        }

    def _normalize_bank_key(self, bank_name: str) -> str:
        return bank_name.lower().strip().replace(" ", "").replace("_", "").replace("-", "")
    
    def get_processor(self, bank_name: str):
        """Get processor for specific bank."""
        bank_key = self._normalize_bank_key(bank_name)
        aliases = {
            "hdfcbank": "hdfc",
            "axisbank": "axis",
            "icicibank": "icici",
            "kotakbank": "kotak",
            "kotakmahindrabank": "kotak",
            "statebankofindia": "sbi",
            "statebank": "sbi",
        }
        bank_key = aliases.get(bank_key, bank_key)
        
        if bank_key not in self._processors:
            raise ValueError(f"Unsupported bank: {bank_name}. Supported banks: {list(self._processors.keys())}")
        
        processor = self._processors[bank_key]
        logger.info("Bank processor selected", bank=bank_key, processor=processor.__class__.__name__)
        
        return processor
    
    def get_supported_banks(self) -> List[str]:
        """Get list of supported banks."""
        return list(self._processors.keys())
    
    def register_processor(self, bank_name: str, processor):
        """Register a new bank processor."""
        self._processors[bank_name.lower()] = processor
        logger.info("Bank processor registered", bank=bank_name)
