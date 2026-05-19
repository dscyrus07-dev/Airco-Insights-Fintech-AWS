"""
Bank processors package initialization.
"""

from .factory import (
    BankProcessorFactory,
    CanaraProcessor,
    IDFCProcessor,
    KarnatakaProcessor,
    PaytmProcessor,
    UnionProcessor,
    BankOfBarodaProcessor,
    UnknownProcessor,
)
from .base_processor import BaseBankProcessor
from .hdfc_processor import HDFCProcessor

# Placeholder implementations for other banks
class AxisProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("axis")
    
    async def process_pdf(self, file_path: str, options: dict) -> dict:
        # TODO: Implement Axis Bank processor
        return {"transactions": [], "metadata": {"bank": "axis"}, "errors": ["Not implemented yet"]}
    
    def validate_pdf(self, file_path: str) -> bool:
        # TODO: Implement Axis validation
        return False

class ICICIProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("icici")
    
    async def process_pdf(self, file_path: str, options: dict) -> dict:
        # TODO: Implement ICICI Bank processor
        return {"transactions": [], "metadata": {"bank": "icici"}, "errors": ["Not implemented yet"]}
    
    def validate_pdf(self, file_path: str) -> bool:
        # TODO: Implement ICICI validation
        return False

class KotakProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("kotak")
    
    async def process_pdf(self, file_path: str, options: dict) -> dict:
        # TODO: Implement Kotak Bank processor
        return {"transactions": [], "metadata": {"bank": "kotak"}, "errors": ["Not implemented yet"]}
    
    def validate_pdf(self, file_path: str) -> bool:
        # TODO: Implement Kotak validation
        return False

class SBIProcessor(BaseBankProcessor):
    def __init__(self):
        super().__init__("sbi")
    
    async def process_pdf(self, file_path: str, options: dict) -> dict:
        # TODO: Implement SBI Bank processor
        return {"transactions": [], "metadata": {"bank": "sbi"}, "errors": ["Not implemented yet"]}
    
    def validate_pdf(self, file_path: str) -> bool:
        # TODO: Implement SBI validation
        return False

__all__ = [
    'BankProcessorFactory',
    'BaseBankProcessor',
    'HDFCProcessor',
    'AxisProcessor',
    'ICICIProcessor',
    'KotakProcessor',
    'SBIProcessor'
    , 'CanaraProcessor',
    'IDFCProcessor',
    'KarnatakaProcessor',
    'PaytmProcessor',
    'UnionProcessor',
    'BankOfBarodaProcessor',
    'UnknownProcessor'
]
