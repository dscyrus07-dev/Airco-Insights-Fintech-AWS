"""
Airco Insights — Shared Formula Excel Engine Base
All bank formula Excel engines inherit from this base class.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FormulaExcelEngineBase:
    """Base class for all bank formula Excel engines."""

    def __init__(self, bank_name: str, report_generator_module: str):
        self.bank_name = bank_name
        self.report_generator_module = report_generator_module
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate HDFC-style Excel report via shared report generator."""
        # Dynamic import to avoid circular dependencies
        import importlib
        report_gen = importlib.import_module(self.report_generator_module)
        generate_report = getattr(report_gen, "generate_report")

        user_info = {
            "full_name": metadata.get("name", ""),
            "account_type": metadata.get("account_type", ""),
            "bank_name": self.bank_name,
        }

        self.logger.info(
            "FormulaExcelEngine: generating %s report for %d transactions",
            self.bank_name, len(transactions)
        )

        generate_report(
            transactions=transactions,
            output_path=output_path,
            user_info=user_info,
        )
        return output_path
