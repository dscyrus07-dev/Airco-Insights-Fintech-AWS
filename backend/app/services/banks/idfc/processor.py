"""Airco Insights — IDFC Bank Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='idfc', bank_name='IDFC Bank', file_prefix='idfc', markers=['idfc first bank', 'idfc bank', 'idfc first', 'idfc'], support_aliases=['idfc', 'idfc bank', 'idfc first', 'idfc first bank'])

class IDFCProcessorError(GenericProcessorError): pass
class IDFCProcessingMetrics(GenericProcessingMetrics): pass
class IDFCProcessingResult(GenericProcessingResult): pass
class IDFCStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class IDFCParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class IDFCTransactionValidator(GenericTransactionValidator): pass
class IDFCReconciliation(GenericReconciliation): pass
class IDFCRecurringEngine(GenericRecurringEngine): pass
class IDFCAggregationEngine(GenericAggregationEngine): pass
class IDFCExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class IDFCAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class IDFCRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class IDFCClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class IDFCFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class IDFCProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
