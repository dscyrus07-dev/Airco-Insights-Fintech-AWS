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


class CanaraProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("canara")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "canara"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class IDFCProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("idfc")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "idfc"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class KarnatakaProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("karnataka")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "karnataka"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class PaytmProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("paytm")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "paytm"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class UnionProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("union")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "union"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class BankOfBarodaProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("bank_of_baroda")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "bank_of_baroda"}, "errors": ["Not implemented yet"]}

    def validate_pdf(self, file_path: str) -> bool:
        return False


class UnknownProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("unknown")

    async def process_pdf(self, file_path: str, options: dict) -> dict:
        return {"transactions": [], "metadata": {"bank": "unknown"}, "errors": ["Not implemented yet"]}

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
            'sbi': SBIProcessor(),
            'canara': CanaraProcessor(),
            'idfc': IDFCProcessor(),
            'karnataka': KarnatakaProcessor(),
            'paytm': PaytmProcessor(),
            'union': UnionProcessor(),
            'bank_of_baroda': BankOfBarodaProcessor(),
            'unknown': UnknownProcessor(),
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
            "canarabank": "canara",
            "idfcbank": "idfc",
            "idfcfirst": "idfc",
            "idfcfirstbank": "idfc",
            "karnatakabank": "karnataka",
            "paytmbank": "paytm",
            "unionbank": "union",
            "unionbankofindia": "union",
            "bankofbaroda": "bank_of_baroda",
            "bob": "bank_of_baroda",
            "unknownbank": "unknown",
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
