from pathlib import Path

root = Path(r'x:\FinTech SAAS\Airco Insights Fintech\backend\app\services\banks')
hdfc_report = root / 'hdfc' / 'report_generator.py'
shared_report = root / '_shared' / 'report_generator_base.py'

text = hdfc_report.read_text(encoding='utf-8')

replacements = [
    ('from typing import Dict, List, Tuple, Any, Optional', 'from typing import Callable, Dict, List, Tuple, Any, Optional'),
    ('from .hdfc_classifier import HDFCClassifier', 'from app.services.banks.hdfc.hdfc_classifier import HDFCClassifier'),
    ('_classifier = None', '_classifier_cache: Dict[str, Any] = {}'),
    (
        'def get_classifier() -> HDFCClassifier:\n    """Get or create the unified HDFC classifier instance."""\n    global _classifier\n    if _classifier is None:\n        _classifier = HDFCClassifier()\n        logger.info("HDFC classifier initialized: %s", _classifier.get_category_stats())\n    return _classifier',
        'def get_classifier(classifier_factory: Optional[Callable[[], Any]] = None, bank_name: str = "HDFC") -> Any:\n    """Get or create the bank-specific classifier instance."""\n    global _classifier_cache\n    if bank_name not in _classifier_cache:\n        _classifier_cache[bank_name] = classifier_factory() if classifier_factory is not None else HDFCClassifier()\n        logger.info("%s classifier initialized: %s", bank_name, _classifier_cache[bank_name].get_category_stats())\n    return _classifier_cache[bank_name]'
    ),
    ('def classify(row) -> Tuple[str, int]:', 'def classify(row, classifier_factory: Optional[Callable[[], Any]] = None, bank_name: str = "HDFC") -> Tuple[str, int]:'),
    ('    learned = _learning_store.lookup(description, bank_name="HDFC")', '    learned = _learning_store.lookup(description, bank_name=bank_name)'),
    ('    classifier = get_classifier()', '    classifier = get_classifier(classifier_factory, bank_name)'),
    ('                bank_name="HDFC",', '                bank_name=bank_name,'),
    ('        logger.debug("HDFC learning-store update skipped", exc_info=True)', '        logger.debug("%s learning-store update skipped", bank_name, exc_info=True)'),
    (
        'def generate_report(\n    transactions: List[Dict[str, Any]],\n    output_path: str,\n    user_info: Optional[Dict[str, Any]] = None,\n) -> Dict[str, Any]:',
        'def generate_report(\n    transactions: List[Dict[str, Any]],\n    output_path: str,\n    user_info: Optional[Dict[str, Any]] = None,\n    classifier_factory: Optional[Callable[[], Any]] = None,\n    bank_name: str = "HDFC",\n) -> Dict[str, Any]:'
    ),
    ('    results = df.apply(classify, axis=1)', '    results = df.apply(lambda row: classify(row, classifier_factory=classifier_factory, bank_name=bank_name), axis=1)'),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f'Missing expected snippet:\n{old[:200]}')
    if old == '    classifier = get_classifier()':
        text = text.replace(old, new, 2)
    else:
        text = text.replace(old, new)

shared_report.parent.mkdir(parents=True, exist_ok=True)
shared_report.write_text(text, encoding='utf-8')

wrapper_template = '''"""
{bank} Bank Transaction Report Generator
=======================================
Thin wrapper around shared base report generator.
Uses {classifier} for transaction categorization.
"""

from typing import Any, Dict, List, Optional, Tuple

from {classifier_module} import {classifier}
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


def get_classifier() -> {classifier}:
    """Get {bank} classifier instance."""
    return {classifier}()


def classify(row) -> Tuple[str, int]:
    """Classify a transaction row using the shared base classifier path."""
    return _base_classify(row, classifier_factory=get_classifier, bank_name={bank_repr})


def generate_report(
    transactions: List[Dict[str, Any]],
    output_path: str,
    user_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate the shared HDFC-style report for {bank} statements."""
    return _base_generate_report(
        transactions=transactions,
        output_path=output_path,
        user_info=user_info,
        classifier_factory=get_classifier,
        bank_name={bank_repr},
    )
'''

banks = {
    'hdfc': ('HDFC', 'HDFCClassifier', 'hdfc_classifier'),
    'axis': ('Axis', 'AxisClassifier', 'axis_classifier'),
    'bank_of_baroda': ('Bank of Baroda', 'BankOfBarodaClassifier', 'bank_of_baroda_classifier'),
    'canara': ('Canara', 'CanaraClassifier', 'canara_classifier'),
    'icici': ('ICICI', 'ICICIClassifier', 'icici_classifier'),
    'idfc': ('IDFC', 'IDFCClassifier', 'idfc_classifier'),
    'karnataka': ('Karnataka', 'KarnatakaClassifier', 'rule_engine'),
    'kotak': ('Kotak', 'KotakClassifier', 'kotak_classifier'),
    'paytm': ('Paytm', 'PaytmClassifier', 'paytm_classifier'),
    'sbi': ('SBI', 'SBIClassifier', 'sbi_classifier'),
    'union': ('Union Bank of India', 'UnionClassifier', 'rule_engine'),
    'unknown': ('Unknown', 'UnknownClassifier', 'unknown_classifier'),
}

for bank_key, (bank_label, classifier_name, classifier_module) in banks.items():
    target = root / bank_key / 'report_generator.py'
    content = wrapper_template.format(
        bank=bank_label,
        classifier=classifier_name,
        classifier_module=f'.{classifier_module}',
        classifier_lower=classifier_name[0].lower() + classifier_name[1:],
        bank_repr=repr(bank_label),
    )
    target.write_text(content, encoding='utf-8')

print('Shared report base and wrappers generated successfully')
