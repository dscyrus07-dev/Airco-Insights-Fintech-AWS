from __future__ import annotations

from typing import Optional

from app.services.banks._shared.generic_bank import GenericAIFallback, GenericBankConfig


CONFIG = GenericBankConfig(
    bank_key="union",
    bank_name="Union Bank of India",
    file_prefix="union",
    markers=["union bank of india", "statement of account", "ubin"],
    support_aliases=["union", "union bank", "union bank of india", "ubi"],
)


class UnionAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(CONFIG, api_key=api_key)

