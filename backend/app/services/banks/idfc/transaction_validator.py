"""
Airco Insights - IDFC Bank Transaction Validator
"""

import logging
from typing import Dict, List, Tuple

from app.services.banks._shared.generic_bank import GenericTransactionValidator, GenericValidationError

logger = logging.getLogger(__name__)


class IDFCTransactionValidator(GenericTransactionValidator):
    pass


# Re-export for compatibility
IDFCValidationError = GenericValidationError
