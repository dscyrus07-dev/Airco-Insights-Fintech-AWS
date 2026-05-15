"""Airco Insights — Paytm Bank Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='paytm', bank_name='Paytm Bank', file_prefix='paytm', markers=['paytm bank', 'paytm payments bank', 'paytm'], support_aliases=['paytm', 'paytm bank', 'paytm payments bank'])

class PaytmProcessorError(GenericProcessorError): pass
class PaytmProcessingMetrics(GenericProcessingMetrics): pass
class PaytmProcessingResult(GenericProcessingResult): pass
class PaytmStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class PaytmParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class PaytmTransactionValidator(GenericTransactionValidator): pass
class PaytmReconciliation(GenericReconciliation): pass
class PaytmRecurringEngine(GenericRecurringEngine): pass
class PaytmAggregationEngine(GenericAggregationEngine): pass
class PaytmExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class PaytmAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class PaytmRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class PaytmClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class PaytmFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class PaytmProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
