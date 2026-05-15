"""Airco Insights — Karnataka Bank Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='karnataka', bank_name='Karnataka Bank', file_prefix='karnataka', markers=['karnataka bank', 'karnataka'], support_aliases=['karnataka', 'karnataka bank'])

class KarnatakaProcessorError(GenericProcessorError): pass
class KarnatakaProcessingMetrics(GenericProcessingMetrics): pass
class KarnatakaProcessingResult(GenericProcessingResult): pass
class KarnatakaStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class KarnatakaParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class KarnatakaTransactionValidator(GenericTransactionValidator): pass
class KarnatakaReconciliation(GenericReconciliation): pass
class KarnatakaRecurringEngine(GenericRecurringEngine): pass
class KarnatakaAggregationEngine(GenericAggregationEngine): pass
class KarnatakaExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class KarnatakaAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class KarnatakaRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class KarnatakaClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class KarnatakaFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class KarnatakaProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
