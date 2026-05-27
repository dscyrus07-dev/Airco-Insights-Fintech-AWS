"""
Canara Bank Transaction Report Generator
=======================================
Thin wrapper around shared base report generator.
Uses CanaraClassifier for transaction categorization.
"""

from typing import Any, Dict, List, Optional, Tuple

from .canara_classifier import CanaraClassifier
from app.services.banks._shared.report_generator_base import (
    CHEQUE_TOKENS,
    classify as _base_classify,
    detect_recurring,
    generate_report as _base_generate_report,
    get_week_bucket,
    _build_category_outcome_frame,
    _build_category_outcome_tables,
    _build_source_analysis_frame,
    _compute_finbit_monthly,
    _detect_transaction_mode,
    _extract_source,
    _flag_transaction,
    _map_identified_category,
    _normalize_text,
)

__all__ = [
    "generate_report",
    "get_classifier",
    "classify",
    "detect_recurring",
    "get_week_bucket",
    "CHEQUE_TOKENS",
    "_normalize_text",
    "_detect_transaction_mode",
    "_extract_source",
    "_map_identified_category",
    "_flag_transaction",
    "_build_source_analysis_frame",
    "_build_category_outcome_frame",
    "_build_category_outcome_tables",
    "_compute_finbit_monthly",
]


def get_classifier() -> CanaraClassifier:
    """Get Canara classifier instance."""
    return CanaraClassifier()


def classify(row) -> Tuple[str, int]:
    """Classify a transaction row using the shared base classifier path."""
    return _base_classify(row, classifier_factory=get_classifier, bank_name='Canara')


def generate_report(
    transactions: List[Dict[str, Any]],
    output_path: str,
    user_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate the shared HDFC-style report for Canara statements."""
    return _base_generate_report(
        transactions=transactions,
        output_path=output_path,
        user_info=user_info,
        classifier_factory=get_classifier,
        bank_name='Canara',
    )
