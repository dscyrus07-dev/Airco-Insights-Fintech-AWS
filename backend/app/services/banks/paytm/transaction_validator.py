"""
Airco Insights - Paytm Bank Transaction Validator
"""

import logging
from typing import Dict, List, Tuple

from app.services.banks._shared.generic_bank import GenericTransactionValidator, GenericValidationError

logger = logging.getLogger(__name__)


class PaytmTransactionValidator(GenericTransactionValidator):
    pass


# Re-export for compatibility
PaytmValidationError = GenericValidationError
