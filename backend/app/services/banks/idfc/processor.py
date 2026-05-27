"""
Airco Insights - IDFC Bank Processor Module
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.banks._shared.data_quality import compute_data_quality
from app.services.banks._shared.generic_bank import (
    GenericBankConfig,
    GenericParseError,
    GenericProcessingMetrics,
    GenericProcessingResult,
    GenericProcessorError,
    GenericReconciliationError,
    GenericStructureError,
    GenericValidationError,
)
from app.services.core.data_integrity_guard import DataIntegrityGuard, IntegrityError
from app.services.core.pdf_integrity_validator import PDFIntegrityError, PDFIntegrityValidator

# Import from extracted modules
from .structure_validator import IDFCStructureValidator
from .parser import IDFCParser, IDFCParseResult, IDFCTransaction
from .transaction_validator import IDFCTransactionValidator
from .reconciliation import IDFCReconciliation
from .rule_engine import IDFCRuleEngine
from .ai_fallback import IDFCAIFallback
from .recurring_engine import IDFCRecurringEngine
from .aggregation_engine import IDFCAggregationEngine
from .excel_generator import IDFCExcelGenerator
from .formula_excel_engine import IDFCFormulaExcelEngine

CONFIG = GenericBankConfig(
    bank_key="idfc",
    bank_name="IDFC Bank",
    file_prefix="idfc",
    markers=["idfc first bank", "idfc bank", "statement of account", "idfb"],
    support_aliases=["idfc", "idfc bank", "idfc first", "idfc first bank"],
)

logger = logging.getLogger(__name__)


class IDFCProcessorError(GenericProcessorError):
    pass


@dataclass
class IDFCProcessingMetrics(GenericProcessingMetrics):
    ai_classified_count: int = 0
    integrity_passed: bool = False


@dataclass
class IDFCProcessingResult(GenericProcessingResult):
    integrity_result: Any = None
    data_quality: str = "high"
    reconciliation_status: str = "passed"
    data_quality_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = super().to_dict()
        payload["stats"]["ai_classified"] = self.metrics.ai_classified_count
        payload["validation"]["integrity_passed"] = self.metrics.integrity_passed
        payload["data_quality"] = self.data_quality
        payload["reconciliation_status"] = self.reconciliation_status
        payload["data_quality_warnings"] = self.data_quality_warnings
        return payload


class IDFCProcessor:
    def __init__(self, strict_mode: bool = True, enable_ai: bool = False, api_key: Optional[str] = None, audit_service=None, job_id: Optional[str] = None):
        self.strict_mode = strict_mode
        self.enable_ai = enable_ai
        self.api_key = api_key
        self.audit_service = audit_service
        self.job_id = job_id

        self.pdf_validator = PDFIntegrityValidator()
        self.structure_validator = IDFCStructureValidator()
        self.parser = IDFCParser(audit_service=audit_service, job_id=job_id)
        self.transaction_validator = IDFCTransactionValidator(strict_mode=False)
        self.reconciliation = IDFCReconciliation(strict_mode=False)
        self.rule_engine = IDFCRuleEngine()
        self.ai_fallback = IDFCAIFallback(api_key=api_key) if (enable_ai and api_key) else None
        self.recurring_engine = IDFCRecurringEngine()
        self.aggregation_engine = IDFCAggregationEngine()
        self.excel_generator = IDFCExcelGenerator()
        self.formula_excel_engine = IDFCFormulaExcelEngine()
        self.integrity_guard = DataIntegrityGuard(strict_mode=strict_mode)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(self, file_path: str, user_info: Dict[str, Any], output_dir: Optional[str] = None) -> IDFCProcessingResult:
        pipeline_start = time.monotonic()
        metrics = IDFCProcessingMetrics()
        try:
            pdf_result = self._time_step("pdf_validation", lambda: self.pdf_validator.validate(file_path), metrics)
            structure_result = self._time_step(
                "structure_validation",
                lambda: self.structure_validator.validate(pdf_result.text_content, pdf_result.first_page_text),
                metrics,
            )
            parse_result = self._time_step("parsing", lambda: self.parser.parse(file_path, pdf_result.text_content), metrics)
            if parse_result.total_count <= 0:
                raise GenericParseError("Could not extract transactions from this IDFC PDF.", error_code="NO_TRANSACTIONS")

            validated, _ = self._time_step(
                "transaction_validation",
                lambda: self.transaction_validator.validate([txn.to_dict() for txn in parse_result.transactions]),
                metrics,
            )
            metrics.transaction_count = len(validated)

            reconciliation = self._time_step(
                "reconciliation",
                lambda: self.reconciliation.reconcile(
                    validated,
                    expected_opening=structure_result.metadata.opening_balance or parse_result.opening_balance,
                    expected_closing=structure_result.metadata.closing_balance or parse_result.closing_balance,
                ),
                metrics,
            )
            metrics.reconciliation_passed = bool(reconciliation.get("passed"))

            processed_transactions, unclassified = self._time_step(
                "classification",
                lambda: self.rule_engine.classify(validated),
                metrics,
            )
            all_transactions = processed_transactions
            metrics.classified_count = len(processed_transactions) - len(unclassified)
            metrics.unclassified_count = len(unclassified)

            if self.enable_ai and self.api_key and self.ai_fallback and unclassified:
                ai_raw, _ = self._time_step(
                    "ai_fallback",
                    lambda: self.ai_fallback.classify(unclassified, CONFIG.bank_name, user_info.get("account_type", "")),
                    metrics,
                )
                ai_results = ai_raw[0] if isinstance(ai_raw, tuple) else ai_raw
                metrics.ai_classified_count = sum(1 for txn in ai_results if not str(txn.get("category", "")).startswith("Others"))
                ai_iter = iter(ai_results)
                merged: List[Dict[str, Any]] = []
                for txn in processed_transactions:
                    if str(txn.get("category", "")).startswith("Others"):
                        merged.append(next(ai_iter, txn))
                    else:
                        merged.append(txn)
                all_transactions = merged
                metrics.unclassified_count = sum(1 for txn in all_transactions if str(txn.get("category", "")).startswith("Others"))

            all_transactions = self._time_step("recurring_detection", lambda: self.recurring_engine.detect(all_transactions), metrics)
            metrics.recurring_count = sum(1 for txn in all_transactions if txn.get("is_recurring"))

            aggregation = self._time_step(
                "aggregation",
                lambda: self.aggregation_engine.aggregate(
                    all_transactions,
                    opening=structure_result.metadata.opening_balance or parse_result.opening_balance,
                    closing=structure_result.metadata.closing_balance or parse_result.closing_balance,
                ),
                metrics,
            )

            try:
                integrity_result = self._time_step(
                    "integrity_check",
                    lambda: self.integrity_guard.validate(
                        all_transactions,
                        expected_count=structure_result.metadata.expected_transaction_count,
                        expected_opening_balance=structure_result.metadata.opening_balance or parse_result.opening_balance,
                        expected_closing_balance=structure_result.metadata.closing_balance or parse_result.closing_balance,
                        expected_total_credits=parse_result.total_credits,
                        expected_total_debits=parse_result.total_debits,
                    ),
                    metrics,
                )
                metrics.integrity_passed = integrity_result.is_valid
            except IntegrityError:
                if self.strict_mode:
                    raise
                integrity_result = None
                metrics.integrity_passed = False

            data_quality, recon_status, dq_warnings = compute_data_quality(
                recon_passed=metrics.reconciliation_passed,
                corrections=0,
                total=len(all_transactions),
                mismatches=0 if reconciliation.get("passed") else 1,
            )

            if output_dir is None:
                output_dir = os.path.dirname(file_path) or "."
            excel_path = os.path.join(output_dir, f"idfc_{uuid.uuid4().hex[:12]}.xlsx")

            formula_transactions = []
            for txn in all_transactions:
                formula_transactions.append({
                    "date": txn.get("date", ""),
                    "description": txn.get("description", ""),
                    "debit": txn.get("debit"),
                    "credit": txn.get("credit"),
                    "balance": txn.get("balance"),
                    "category": txn.get("category", ""),
                    "confidence": txn.get("confidence", ""),
                    "recurring": "Yes" if txn.get("recurring", False) else "No",
                })

            metadata = {
                "name": user_info.get("full_name") or user_info.get("name") or "",
                "account_no": user_info.get("account_no") or user_info.get("account_number") or "",
                "account_type": user_info.get("account_type", ""),
                "bank_name": CONFIG.bank_name,
                "opening_balance": getattr(aggregation, "opening_balance", 0),
                "closing_balance": getattr(aggregation, "closing_balance", 0),
                "total_credits": getattr(aggregation, "total_credits", 0),
                "total_debits": getattr(aggregation, "total_debits", 0),
                "total_transactions": len(formula_transactions),
                "data_quality": data_quality.value,
                "reconciliation_status": recon_status,
                "data_quality_warnings": dq_warnings,
            }

            try:
                self._time_step(
                    "excel_generation",
                    lambda: self.formula_excel_engine.generate(formula_transactions, metadata, excel_path),
                    metrics,
                )

            except Exception:
                self.logger.warning("Formula Excel generation failed for IDFC, falling back to legacy generator", exc_info=True)
                excel_user_info = dict(user_info or {})
                excel_user_info["data_quality"] = data_quality.value
                excel_user_info["reconciliation_status"] = recon_status
                excel_user_info["data_quality_warnings"] = dq_warnings
                self._time_step(
                    "excel_generation",
                    lambda: self.excel_generator.generate(all_transactions, aggregation, excel_user_info, excel_path),
                    metrics,
                )

            metrics.total_time_ms = round((time.monotonic() - pipeline_start) * 1000, 1)

            if self.audit_service and self.job_id:
                try:
                    self.audit_service.finalize_job_audit(
                        self.job_id,
                        hygiene_result=getattr(self.parser, '_hygiene_result', None),
                        parser_metrics_collected=getattr(self.parser, '_collected_parser_metrics', []),
                        raw_transactions=all_transactions,
                        excel_path=excel_path,
                        sheet_count=11,
                        template_used='IDFC_FREE',
                        generation_time_ms=int(metrics.step_timings.get('excel_generation', 0)),
                        transaction_count=len(all_transactions),
                        classified_transactions=all_transactions,
                        statement_header={
                            "userid": (user_info or {}).get("user_id"),
                            "filename": (file_path or "").replace("\\", "/").rsplit("/", 1)[-1],
                            "bankname": getattr(self.parser, "BANK_NAME", "IDFC"),
                            "accountno": (user_info or {}).get("account_number") or (user_info or {}).get("account_no"),
                            "formatidentify": getattr(getattr(self.parser, "_hygiene_result", None), "format_id", None),
                        },
                    )
                except Exception as _ae:
                    self.logger.error('finalize_job_audit failed (non-fatal): %s', _ae, exc_info=True)

            return IDFCProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=all_transactions,
                aggregation=aggregation,
                metrics=metrics,
                bank_key=CONFIG.bank_key,
                integrity_result=integrity_result,
                data_quality=data_quality.value,
                reconciliation_status=recon_status,
                data_quality_warnings=dq_warnings,
            )
        except Exception as exc:
            self.logger.error("IDFC processing failed", exc_info=True)
            if isinstance(exc, PDFIntegrityError):
                error_code = exc.error_code
            elif isinstance(exc, (GenericStructureError, GenericParseError, GenericValidationError, GenericReconciliationError)):
                error_code = getattr(exc, "error_code", "PROCESSING_ERROR")
            elif isinstance(exc, IntegrityError):
                error_code = "INTEGRITY_FAILED"
            else:
                error_code = "PROCESSING_ERROR"
            metrics.total_time_ms = round((time.monotonic() - pipeline_start) * 1000, 1)
            return IDFCProcessingResult(
                status="failed",
                excel_path=None,
                transactions=[],
                aggregation=None,
                metrics=metrics,
                bank_key=CONFIG.bank_key,
                error_message=str(exc),
                error_code=error_code,
            )

    def _time_step(self, step_name: str, func, metrics: IDFCProcessingMetrics):
        started = time.time()
        result = func()
        metrics.step_timings[step_name] = round((time.time() - started) * 1000, 1)
        return result
