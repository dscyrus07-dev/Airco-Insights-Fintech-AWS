"""
Airco Insights — Paytm Payments Bank Formula Excel Engine (Thin Wrapper)
"""

import logging
from typing import List, Dict, Any

from app.services.banks._shared.formula_excel_engine_base import FormulaExcelEngineBase

logger = logging.getLogger(__name__)


class PaytmFormulaExcelEngine(FormulaExcelEngineBase):
    """Paytm Formula Excel Engine — delegates to shared base."""

    def __init__(self):
        super().__init__(
            bank_name="Paytm Payments Bank",
            report_generator_module="app.services.banks.paytm.report_generator"
        )


# Backward compatibility alias for processor imports
FormulaExcelEngine = PaytmFormulaExcelEngine
