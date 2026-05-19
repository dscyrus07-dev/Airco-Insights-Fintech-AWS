"""
Airco Insights - SBI Bank Processor
===================================
Complete SBI bank statement processor aligned with the HDFC-style pipeline.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.banks._shared.data_quality import compute_data_quality
from app.services.core.data_integrity_guard import DataIntegrityGuard, IntegrityError
from app.services.core.pdf_integrity_validator import PDFIntegrityError, PDFIntegrityValidator

from .aggregation_engine import SBIAggregationEngine
from .ai_fallback import SBIAIFallback
from .excel_generator import SBIExcelGenerator
from .formula_excel_engine import SBIFormulaExcelEngine
from .parser import SBIParseError, SBIParser
from .reconciliation import SBIReconciliation, SBIReconciliationError
from .recurring_engine import SBIRecurringEngine
from .rule_engine import SBIRuleEngine
from .structure_validator import SBIStructureError, SBIStructureValidator
from .transaction_validator import SBITransactionValidator, SBIValidationError

logger = logging.getLogger(__name__)


class SBIProcessorError(Exception):
    def __init__(self, message: str, stage: str, error_code: str, details: dict = None):
        self.stage = stage
        self.error_code = error_code
        self.details = details or {}
        super().__init__(f"[{stage}] {message}")


@dataclass
class SBIProcessingMetrics:
    total_time_ms: float = 0
    step_timings: Dict[str, float] = field(default_factory=dict)
    transaction_count: int = 0
    classified_count: int = 0
    unclassified_count: int = 0
    ai_classified_count: int = 0
    recurring_count: int = 0
    reconciliation_passed: bool = False
    integrity_passed: bool = False
    corrections_made: int = 0


@dataclass
class SBIProcessingResult:
    status: str
    excel_path: Optional[str]
    transactions: List[Dict[str, Any]]
    aggregation: Any
    metrics: SBIProcessingMetrics
    integrity_result: Any = None
    data_quality: str = "high"
    reconciliation_status: str = "passed"
    data_quality_warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "excel_path": self.excel_path,
            "stats": {
                "total_transactions": self.metrics.transaction_count,
                "rule_engine_classified": self.metrics.classified_count,
                "ai_classified": self.metrics.ai_classified_count,
                "others": self.metrics.unclassified_count,
                "recurring": self.metrics.recurring_count,
                "coverage_percent": round(
                    (self.metrics.classified_count + self.metrics.ai_classified_count)
                    / max(self.metrics.transaction_count, 1)
                    * 100,
                    1,
                ),
            },
            "validation": {
                "reconciliation_passed": self.metrics.reconciliation_passed,
                "integrity_passed": self.metrics.integrity_passed,
            },
            "data_quality": self.data_quality,
            "reconciliation_status": self.reconciliation_status,
            "data_quality_warnings": self.data_quality_warnings,
            "performance": self.metrics.step_timings,
            "error": {"message": self.error_message, "code": self.error_code}
            if self.error_message
            else None,
        }


class SBIProcessor:
    """Master controller for SBI statement processing."""

    def __init__(
        self,
        strict_mode: bool = True,
        enable_ai: bool = False,
        api_key: Optional[str] = None,
    ):
        self.strict_mode = strict_mode
        self.enable_ai = enable_ai
        self.api_key = api_key

        self.pdf_validator = PDFIntegrityValidator()
        self.structure_validator = SBIStructureValidator()
        self.parser = SBIParser()
        self.transaction_validator = SBITransactionValidator(strict_mode=False)
        self.reconciliation = SBIReconciliation(strict_mode=False)
        self.rule_engine = SBIRuleEngine()
        self.ai_fallback = SBIAIFallback(api_key=api_key) if (enable_ai and api_key) else None
        self.recurring_engine = SBIRecurringEngine()
        self.aggregation_engine = SBIAggregationEngine()
        self.excel_generator = SBIExcelGenerator()
        self.formula_excel_engine = SBIFormulaExcelEngine()
        self.integrity_guard = DataIntegrityGuard(strict_mode=strict_mode)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(
        self,
        file_path: str,
        user_info: Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> SBIProcessingResult:
        pipeline_start = time.monotonic()
        metrics = SBIProcessingMetrics()
        return self._process_pipeline(file_path, user_info, output_dir, metrics, pipeline_start)

    def _process_pipeline(
        self,
        file_path: str,
        user_info: Dict[str, Any],
        output_dir: Optional[str],
        metrics: SBIProcessingMetrics,
        pipeline_start: float,
    ) -> SBIProcessingResult:
        try:
            pdf_result = self._time_step("pdf_validation", lambda: self.pdf_validator.validate(file_path), metrics)

            structure_result = self._time_step(
                "structure_validation",
                lambda: self.structure_validator.validate(
                    pdf_result.text_content,
                    pdf_result.first_page_text,
                ),
                metrics,
            )
            statement_metadata = structure_result.metadata

            parse_result = self._time_step("parsing", lambda: self.parser.parse(file_path, pdf_result.text_content), metrics)
            if parse_result.total_count <= 0:
                raise SBIParseError(
                    "Could not extract any transactions from this SBI PDF. Please upload a text-based SBI statement downloaded from internet banking.",
                    error_code="NO_TRANSACTIONS",
                )

            metrics.transaction_count = parse_result.total_count

            validation_result = self._time_step(
                "transaction_validation",
                lambda: self.transaction_validator.validate(parse_result.transactions),
                metrics,
            )
            transactions = validation_result.validated_transactions

            transactions, corrections = self.reconciliation.auto_correct_debit_credit(transactions)
            metrics.corrections_made = corrections

            try:
                recon_result = self._time_step(
                    "reconciliation",
                    lambda: self.reconciliation.reconcile(
                        transactions,
                        expected_opening=statement_metadata.opening_balance
                        if statement_metadata.opening_balance is not None
                        else parse_result.opening_balance,
                        expected_closing=statement_metadata.closing_balance
                        if statement_metadata.closing_balance is not None
                        else parse_result.closing_balance,
                        expected_credits=parse_result.total_credits,
                        expected_debits=parse_result.total_debits,
                    ),
                    metrics,
                )
                metrics.reconciliation_passed = recon_result.is_reconciled
            except SBIReconciliationError as exc:
                if self.strict_mode:
                    raise
                self.logger.warning("Reconciliation warning: %s", str(exc))
                metrics.reconciliation_passed = False
                recon_result = None

            classified, unclassified = self._time_step(
                "classification",
                lambda: self.rule_engine.classify(transactions),
                metrics,
            )

            all_transactions = list(classified)
            metrics.classified_count = len(classified)

            if self.enable_ai and self.api_key and self.ai_fallback and unclassified:
                ai_transactions = self._time_step(
                    "ai_fallback",
                    lambda: self.ai_fallback.classify_unclassified(unclassified),
                    metrics,
                )
                metrics.ai_classified_count = sum(
                    1 for txn in ai_transactions if not str(txn.get("category", "")).startswith("Others")
                )
                all_transactions.extend(ai_transactions)
            else:
                all_transactions.extend(unclassified)

            metrics.unclassified_count = sum(
                1 for txn in all_transactions if str(txn.get("category", "")).startswith("Others")
            )

            all_transactions = self._time_step(
                "recurring_detection",
                lambda: self.recurring_engine.detect(all_transactions),
                metrics,
            )
            metrics.recurring_count = sum(1 for txn in all_transactions if txn.get("is_recurring"))

            aggregation = self._time_step(
                "aggregation",
                lambda: self.aggregation_engine.aggregate(
                    all_transactions,
                    opening_balance=recon_result.opening_balance
                    if recon_result and recon_result.opening_balance is not None
                    else (statement_metadata.opening_balance or parse_result.opening_balance or 0),
                    closing_balance=recon_result.closing_balance
                    if recon_result and recon_result.closing_balance is not None
                    else (statement_metadata.closing_balance or parse_result.closing_balance or 0),
                ),
                metrics,
            )

            try:
                integrity_result = self._time_step(
                    "integrity_check",
                    lambda: self.integrity_guard.validate(
                        all_transactions,
                        expected_count=statement_metadata.expected_transaction_count,
                        expected_opening_balance=statement_metadata.opening_balance
                        if statement_metadata.opening_balance is not None
                        else parse_result.opening_balance,
                        expected_closing_balance=statement_metadata.closing_balance
                        if statement_metadata.closing_balance is not None
                        else parse_result.closing_balance,
                        expected_total_credits=parse_result.total_credits,
                        expected_total_debits=parse_result.total_debits,
                    ),
                    metrics,
                )
                metrics.integrity_passed = integrity_result.is_valid
            except IntegrityError as exc:
                if self.strict_mode:
                    raise
                self.logger.warning("Integrity check warning: %s", str(exc))
                integrity_result = None
                metrics.integrity_passed = False

            data_quality, recon_status, dq_warnings = compute_data_quality(
                recon_passed=metrics.reconciliation_passed,
                corrections=metrics.corrections_made,
                total=len(all_transactions),
                mismatches=len(getattr(recon_result, "mismatches", [])) if recon_result else 0,
            )

            if output_dir is None:
                output_dir = os.path.dirname(file_path) or "."
            excel_filename = f"sbi_report_{uuid.uuid4().hex[:12]}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)

            # Convert transactions to formula engine format
            formula_transactions = []
            for txn in all_transactions:
                formula_transactions.append({
                    'date': txn.get('date', ''),
                    'description': txn.get('description', ''),
                    'debit': txn.get('debit'),
                    'credit': txn.get('credit'),
                    'balance': txn.get('balance'),
                    'category': txn.get('category', ''),
                    'confidence': txn.get('confidence', ''),
                    'recurring': 'Yes' if txn.get('recurring', False) else 'No',
                })
            
            # Use formula-based Excel engine
            metadata = {
                'name': user_info.get('full_name') or user_info.get('name', ''),
                'account_no': statement_metadata.account_number or user_info.get('account_number', ''),
            }

            data_quality, recon_status, dq_warnings = compute_data_quality(
                recon_passed=metrics.reconciliation_passed,
                corrections=metrics.corrections_made,
                total=len(all_transactions),
                mismatches=len(getattr(recon_result, "mismatches", [])) if recon_result else 0,
            )
            metadata.update({
                'data_quality': data_quality.value,
                'reconciliation_status': recon_status,
                'data_quality_warnings': "; ".join(dq_warnings) if dq_warnings else "None",
            })

            self._time_step(
                "excel_generation",
                lambda: self._generate_excel(
                    formula_transactions,
                    excel_path,
                    metadata=metadata,
                    aggregation=aggregation,
                ),
                metrics,
            )

            metrics.transaction_count = len(all_transactions)
            metrics.total_time_ms = (time.monotonic() - pipeline_start) * 1000

            return SBIProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=all_transactions,
                aggregation=aggregation,
                metrics=metrics,
                integrity_result=integrity_result,
                data_quality=data_quality.value,
                reconciliation_status=recon_status,
                data_quality_warnings=dq_warnings,
            )

        except PDFIntegrityError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), exc.error_code)
        except SBIStructureError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), exc.error_code)
        except SBIParseError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), exc.error_code)
        except SBIValidationError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), exc.error_code)
        except SBIReconciliationError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), exc.error_code)
        except IntegrityError as exc:
            return self._failure_result(metrics, pipeline_start, str(exc), "INTEGRITY_FAILED")
        except Exception as exc:
            self.logger.error("Unexpected SBI processing failure", exc_info=True)
            return self._failure_result(metrics, pipeline_start, f"Unexpected error: {exc}", "UNEXPECTED_ERROR")

    def _generate_excel(
        self,
        transactions: List[Dict[str, Any]],
        excel_path: str,
        metadata: Dict[str, Any],
        aggregation: Any = None,
    ) -> str:
        parent_dir = os.path.dirname(excel_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        try:
            self.logger.info("SBI: Using formula-based Excel engine")
            return self.formula_excel_engine.generate(transactions, metadata, excel_path)
        except Exception as e:
            self.logger.error("Formula Excel generation failed for SBI: %s", str(e), exc_info=True)
            self.logger.warning("Formula Excel generation failed for SBI, falling back to legacy generator")
            return self.excel_generator.generate(transactions, aggregation, None, excel_path)

    def _failure_result(
        self,
        metrics: SBIProcessingMetrics,
        pipeline_start: float,
        message: str,
        error_code: str,
    ) -> SBIProcessingResult:
        metrics.total_time_ms = (time.monotonic() - pipeline_start) * 1000
        return SBIProcessingResult(
            status="failed",
            excel_path=None,
            transactions=[],
            aggregation=None,
            metrics=metrics,
            error_message=message,
            error_code=error_code,
        )

    def _time_step(self, step_name: str, func, metrics: SBIProcessingMetrics):
        started = time.time()
        result = func()
        metrics.step_timings[step_name] = (time.time() - started) * 1000
        return result
