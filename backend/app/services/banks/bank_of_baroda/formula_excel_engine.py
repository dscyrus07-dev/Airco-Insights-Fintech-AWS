"""
Airco Insights — Bank of Baroda Formula Excel Engine (Thin Wrapper)
"""

import logging
from typing import List, Dict, Any

from app.services.banks._shared.formula_excel_engine_base import FormulaExcelEngineBase

logger = logging.getLogger(__name__)


class BankOfBarodaFormulaExcelEngine(FormulaExcelEngineBase):
    """Bank of Baroda Formula Excel Engine — delegates to shared base."""

    def __init__(self):
        super().__init__(
            bank_name="Bank of Baroda",
            report_generator_module="app.services.banks.bank_of_baroda.report_generator"
        )


# Backward compatibility alias for processor imports
FormulaExcelEngine = BankOfBarodaFormulaExcelEngine
