"""Airco Insights — Canara Bank Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='canara', bank_name='Canara Bank', file_prefix='canara', markers=['canara bank', 'canara'], support_aliases=['canara', 'canara bank'])

class CanaraProcessorError(GenericProcessorError): pass
class CanaraProcessingMetrics(GenericProcessingMetrics): pass
class CanaraProcessingResult(GenericProcessingResult): pass
class CanaraStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class CanaraParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class CanaraTransactionValidator(GenericTransactionValidator): pass
class CanaraReconciliation(GenericReconciliation): pass
class CanaraRecurringEngine(GenericRecurringEngine): pass
class CanaraAggregationEngine(GenericAggregationEngine): pass
class CanaraExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class CanaraAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class CanaraRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class CanaraClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class CanaraFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class CanaraProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
