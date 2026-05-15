"""Airco Insights — Unknown Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='unknown', bank_name='Unknown', file_prefix='unknown', markers=[], support_aliases=['unknown', 'unknown bank'])

class UnknownProcessorError(GenericProcessorError): pass
class UnknownProcessingMetrics(GenericProcessingMetrics): pass
class UnknownProcessingResult(GenericProcessingResult): pass
class UnknownStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class UnknownParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class UnknownTransactionValidator(GenericTransactionValidator): pass
class UnknownReconciliation(GenericReconciliation): pass
class UnknownRecurringEngine(GenericRecurringEngine): pass
class UnknownAggregationEngine(GenericAggregationEngine): pass
class UnknownExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class UnknownAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class UnknownRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class UnknownClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class UnknownFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class UnknownProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
