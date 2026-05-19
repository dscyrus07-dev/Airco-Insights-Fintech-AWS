"""
Bank report generator factory for creating bank-specific report generators.
"""

from typing import Dict, List, Any
from openpyxl import Workbook
from .hdfc_generator import HDFCReportGenerator
from .axis_generator import AxisReportGenerator
from .icici_generator import ICICIReportGenerator
from .kotak_generator import KotakReportGenerator
from .sbi_generator import SBIReportGenerator
from .base_generator import BaseBankReportGenerator
from ...utils.logging import get_logger

logger = get_logger(__name__)


class GenericBankReportGenerator(BaseBankReportGenerator):
    """Fallback report generator for banks that use the standard workbook layout."""

    def __init__(self, bank_name: str):
        super().__init__(bank_name)

    async def generate_sheets(
        self,
        workbook: Workbook,
        transactions: List[Dict[str, Any]],
        user_info: Dict[str, Any],
        ai_results: Any,
        options: Dict[str, Any],
    ) -> List[str]:
        created_sheets = [
            self._create_transactions_sheet(workbook, transactions),
            self._create_summary_sheet(workbook, transactions),
            self._create_category_analysis_sheet(workbook, transactions),
        ]
        return created_sheets

class BankReportGeneratorFactory:
    """Factory for creating bank-specific report generators."""
    
    def __init__(self):
        self._generators: Dict[str, object] = {
            'hdfc': HDFCReportGenerator(),
            'axis': AxisReportGenerator(),
            'icici': ICICIReportGenerator(),
            'kotak': KotakReportGenerator(),
            'sbi': SBIReportGenerator(),
            'canara': GenericBankReportGenerator('canara'),
            'idfc': GenericBankReportGenerator('idfc'),
            'karnataka': GenericBankReportGenerator('karnataka'),
            'paytm': GenericBankReportGenerator('paytm'),
            'union': GenericBankReportGenerator('union'),
            'bank_of_baroda': GenericBankReportGenerator('bank_of_baroda'),
            'unknown': GenericBankReportGenerator('unknown'),
        }

    def _normalize_bank_key(self, bank_name: str) -> str:
        return bank_name.lower().strip().replace(" ", "").replace("_", "").replace("-", "")
    
    def get_generator(self, bank_name: str):
        """Get generator for specific bank."""
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
        
        if bank_key not in self._generators:
            raise ValueError(f"Unsupported bank: {bank_name}. Supported banks: {list(self._generators.keys())}")
        
        generator = self._generators[bank_key]
        logger.info("Bank report generator selected", bank=bank_key, generator=generator.__class__.__name__)
        
        return generator
    
    def get_supported_banks(self) -> List[str]:
        """Get list of supported banks."""
        return list(self._generators.keys())
    
    def register_generator(self, bank_name: str, generator):
        """Register a new bank report generator."""
        self._generators[bank_name.lower()] = generator
        logger.info("Bank report generator registered", bank=bank_name)
