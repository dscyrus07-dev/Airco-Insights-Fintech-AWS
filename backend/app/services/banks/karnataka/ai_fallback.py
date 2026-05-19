from __future__ import annotations

from typing import Optional

from app.services.banks._shared.generic_bank import GenericAIFallback, GenericBankConfig


CONFIG = GenericBankConfig(
    bank_key="karnataka",
    bank_name="Karnataka Bank",
    file_prefix="karnataka",
    markers=["karnataka bank", "statement for a/c", "karb"],
    support_aliases=["karnataka", "karnataka bank"],
)


class KarnatakaAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(CONFIG, api_key=api_key)

