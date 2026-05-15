"""Airco Insights — Bank of Baroda Processor Module"""

from __future__ import annotations

from typing import Optional

from .._shared.generic_bank import (GenericAIFallback, GenericAggregationEngine, GenericBankConfig, GenericClassifier, GenericExcelGenerator, GenericParseError, GenericParseResult, GenericParser, GenericProcessingMetrics, GenericProcessingResult, GenericProcessor, GenericProcessorError, GenericReconciliation, GenericReconciliationError, GenericRecurringEngine, GenericRuleEngine, GenericStructureError, GenericStructureMetadata, GenericStructureResult, GenericStructureValidator, GenericTransaction, GenericTransactionValidator, GenericValidationError, generate_report as _generate_report)

CONFIG = GenericBankConfig(bank_key='bank_of_baroda', bank_name='Bank of Baroda', file_prefix='bank_of_baroda', markers=['bank of baroda', 'baroda', 'bob'], support_aliases=['bank of baroda', 'bankofbaroda', 'bob', 'baroda'])

class BankOfBarodaProcessorError(GenericProcessorError): pass
class BankOfBarodaProcessingMetrics(GenericProcessingMetrics): pass
class BankOfBarodaProcessingResult(GenericProcessingResult): pass
class BankOfBarodaStructureValidator(GenericStructureValidator):
    def __init__(self): super().__init__(CONFIG)
class BankOfBarodaParser(GenericParser):
    def __init__(self): super().__init__(CONFIG)
class BankOfBarodaTransactionValidator(GenericTransactionValidator): pass
class BankOfBarodaReconciliation(GenericReconciliation): pass
class BankOfBarodaRecurringEngine(GenericRecurringEngine): pass
class BankOfBarodaAggregationEngine(GenericAggregationEngine): pass
class BankOfBarodaExcelGenerator(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class BankOfBarodaAIFallback(GenericAIFallback):
    def __init__(self, api_key: Optional[str] = None): super().__init__(CONFIG, api_key=api_key)
class BankOfBarodaRuleEngine(GenericRuleEngine):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class BankOfBarodaClassifier(GenericClassifier):
    def __init__(self, keywords_file: Optional[str] = None): super().__init__(CONFIG, keywords_file=keywords_file)
class BankOfBarodaFormulaExcelEngine(GenericExcelGenerator):
    def __init__(self): super().__init__(CONFIG)
class BankOfBarodaProcessor(GenericProcessor):
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None): super().__init__(CONFIG, strict_mode=strict_mode, enable_ai=enable_ai, api_key=api_key)

def generate_report(transactions, output_path, user_info): return _generate_report(transactions, output_path, user_info, CONFIG)
