"""
Airco Insights - Paytm Bank Reconciliation
"""

import logging
from typing import Dict, List

from app.services.banks._shared.generic_bank import GenericReconciliation, GenericReconciliationError

logger = logging.getLogger(__name__)


class PaytmReconciliation(GenericReconciliation):
    pass


# Re-export for compatibility
PaytmReconciliationError = GenericReconciliationError
