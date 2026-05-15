"""Airco Insights — Union Bank of India Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='union', bank_name='Union Bank of India', file_prefix='union', markers=['union bank of india', 'union bank', 'ubi'], support_aliases=['union', 'union bank', 'union bank of india', 'ubi'])

class UnionProcessorError(GenericProcessorError): pass
class UnionProcessingMetrics(GenericProcessingMetrics): pass
class UnionProcessingResult(GenericProcessingResult): pass
class UnionStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class UnionParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class UnionTransactionValidator(GenericTransactionValidator): pass
class UnionReconciliation(GenericReconciliation): pass
class UnionRecurringEngine(GenericRecurringEngine): pass
class UnionAggregationEngine(GenericAggregationEngine): pass
class UnionExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class UnionAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class UnionRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class UnionClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class UnionFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class UnionProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
