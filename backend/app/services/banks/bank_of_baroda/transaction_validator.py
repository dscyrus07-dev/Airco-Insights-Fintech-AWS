"""
Airco Insights - Bank of Baroda Transaction Validator
"""

import logging
from typing import Dict, List, Tuple

from app.services.banks._shared.generic_bank import GenericTransactionValidator, GenericValidationError

logger = logging.getLogger(__name__)


class BankOfBarodaTransactionValidator(GenericTransactionValidator):
    def __init__(self, strict_mode: bool = False):
        super().__init__(strict_mode=strict_mode)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate(self, transactions: List[Dict]) -> Tuple[List[Dict], Dict]:
        validated = []
        stats = {"total": len(transactions), "valid": 0, "invalid": 0, "warnings": 0}

        for txn in transactions:
            validation_result = self._validate_single(txn)
            if validation_result["valid"]:
                validated.append(txn)
                stats["valid"] += 1
            else:
                if not self.strict_mode:
                    validated.append(txn)
                stats["invalid"] += 1
                stats["warnings"] += len(validation_result["warnings"])

        return validated, stats

    def _validate_single(self, txn: Dict) -> Dict:
        result = {"valid": True, "warnings": []}

        if not txn.get("date"):
            result["valid"] = False
            result["warnings"].append("Missing date")

        if not txn.get("description"):
            result["valid"] = False
            result["warnings"].append("Missing description")

        debit = txn.get("debit") or 0
        credit = txn.get("credit") or 0

        if debit == 0 and credit == 0:
            result["valid"] = False
            result["warnings"].append("No debit or credit amount")

        if debit > 0 and credit > 0:
            result["valid"] = False
            result["warnings"].append("Both debit and credit set")

        if txn.get("balance") is None:
            result["valid"] = False
            result["warnings"].append("Missing balance")

        return result


# Re-export for compatibility
BankOfBarodaValidationError = GenericValidationError
