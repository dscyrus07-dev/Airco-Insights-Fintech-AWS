"""
Airco Insights - IDFC Bank Reconciliation
"""

import logging
from typing import Dict, List

from app.services.banks._shared.generic_bank import GenericReconciliation, GenericReconciliationError

logger = logging.getLogger(__name__)


class IDFCReconciliation(GenericReconciliation):
    pass


# Re-export for compatibility
IDFCReconciliationError = GenericReconciliationError
