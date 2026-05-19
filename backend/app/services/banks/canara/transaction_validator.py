"""
Airco Insights - Canara Bank Transaction Validator
"""

import logging
from typing import Dict, List, Tuple

from app.services.banks._shared.generic_bank import GenericTransactionValidator, GenericValidationError

logger = logging.getLogger(__name__)


class CanaraTransactionValidator(GenericTransactionValidator):
    pass


# Re-export for compatibility
CanaraValidationError = GenericValidationError
