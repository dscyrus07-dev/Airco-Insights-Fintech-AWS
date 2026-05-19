"""
Airco Insights — IDFC Excel Generator
=========================================
Wrapper for IDFC formula-based Excel engine.
Delegates to IDFCFormulaExcelEngine for report generation.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class IDFCExcelGenerator:
    """Excel report generator wrapper for IDFC transactions."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate(
        self,
        transactions: List[Dict[str, Any]],
        aggregation: Any,
        user_info: Optional[Dict[str, Any]] = None,
        output_path: str = None,
    ) -> str:
        """Generate Excel report using formula-based engine."""
        from .formula_excel_engine import IDFCFormulaExcelEngine

        user_info = dict(user_info or {})
        metadata: Dict[str, Any] = {
            "name": user_info.get("full_name") or user_info.get("name") or "",
            "account_no": user_info.get("account_no") or user_info.get("account_number") or "",
            "account_type": user_info.get("account_type") or "",
            "bank_name": "IDFC Bank",
        }

        if aggregation:
            metadata["opening_balance"] = getattr(aggregation, "opening_balance", 0)
            metadata["closing_balance"] = getattr(aggregation, "closing_balance", 0)
            metadata["total_credits"] = getattr(aggregation, "total_credits", 0)
            metadata["total_debits"] = getattr(aggregation, "total_debits", 0)

        metadata["data_quality"] = user_info.get("data_quality", "High")
        metadata["reconciliation_status"] = user_info.get("reconciliation_status", "Passed")
        metadata["data_quality_warnings"] = user_info.get("data_quality_warnings", [])
        metadata["total_transactions"] = len(transactions)

        self.logger.info("IDFCExcelGenerator: generating unified workbook")
        return IDFCFormulaExcelEngine().generate(transactions, metadata, output_path)
