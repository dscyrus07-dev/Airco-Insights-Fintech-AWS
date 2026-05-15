"""
Airco Insights — ICICI Bank Processor (Master Controller)
==========================================================
Complete, self-contained ICICI Bank statement processor.
"""

import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .structure_validator import ICICIStructureValidator, ICICIStructureError
from .parser import ICICIParser, ICICIParseError
from .transaction_validator import ICICITransactionValidator, ICICIValidationError
from .reconciliation import ICICIReconciliation, ICICIReconciliationError
from .rule_engine import ICICIRuleEngine
from .ai_fallback import ICICIAIFallback
from .recurring_engine import ICICIRecurringEngine
from .aggregation_engine import ICICIAggregationEngine
from .excel_generator import ICICIExcelGenerator
from .formula_excel_engine import FormulaExcelEngine
from app.services.banks._shared.data_quality import compute_data_quality

logger = logging.getLogger(__name__)


class ICICIProcessorError(Exception):
    def __init__(self, message: str, stage: str, error_code: str, details: dict = None):
        self.stage      = stage
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(f"[{stage}] {message}")


@dataclass
class ICICIProcessingMetrics:
    total_time_ms:         float = 0
    step_timings:          Dict[str, float] = field(default_factory=dict)
    transaction_count:     int = 0
    classified_count:      int = 0
    unclassified_count:    int = 0
    ai_classified_count:   int = 0
    recurring_count:       int = 0
    reconciliation_passed: bool = False
    corrections_made:      int = 0


@dataclass
class ICICIProcessingResult:
    status:        str
    excel_path:    Optional[str]
    transactions:  List[Dict[str, Any]]
    aggregation:   Any
    metrics:       ICICIProcessingMetrics
    data_quality: str = "high"
    reconciliation_status: str = "passed"
    data_quality_warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_code:    Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status":     self.status,
            "excel_path": self.excel_path,
            "stats": {
                "total_transactions": self.metrics.transaction_count,
                "rule_engine_classified": self.metrics.classified_count,
                "ai_classified": self.metrics.ai_classified_count,
                "others":             self.metrics.unclassified_count,
                "recurring":          self.metrics.recurring_count,
                "coverage_percent": round(
                    (self.metrics.classified_count + self.metrics.ai_classified_count) /
                    max(self.metrics.transaction_count, 1) * 100, 1
                ),
            },
            "validation": {"reconciliation_passed": self.metrics.reconciliation_passed},
            "data_quality": self.data_quality,
            "reconciliation_status": self.reconciliation_status,
            "data_quality_warnings": self.data_quality_warnings,
            "performance": self.metrics.step_timings,
            "error": {"message": self.error_message, "code": self.error_code}
            if self.error_message else None,
        }


class ICICIProcessor:
    """Master controller for ICICI Bank statement processing."""

    def __init__(
        self,
        strict_mode: bool = True,
        enable_ai:   bool = False,
        api_key:     Optional[str] = None,
    ):
        self.strict_mode = strict_mode
        self.enable_ai   = enable_ai
        self.api_key     = api_key

        self.structure_validator   = ICICIStructureValidator()
        self.parser                = ICICIParser()
        self.transaction_validator = ICICITransactionValidator(strict_mode=False)
        self.reconciliation        = ICICIReconciliation(strict_mode=False)
        self.rule_engine           = ICICIRuleEngine()
        self.ai_fallback           = ICICIAIFallback(api_key=api_key)
        self.recurring_engine      = ICICIRecurringEngine()
        self.aggregation_engine    = ICICIAggregationEngine()
        self.excel_generator       = ICICIExcelGenerator()
        self.formula_excel_engine  = FormulaExcelEngine()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(
        self,
        file_path:  str,
        user_info:  Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> ICICIProcessingResult:
        """Process ICICI Bank statement end-to-end."""
        pipeline_start = time.monotonic()
        metrics        = ICICIProcessingMetrics()
        return self._process_free_mode(file_path, user_info, output_dir, metrics, pipeline_start)

    def _process_free_mode(
        self,
        file_path:      str,
        user_info:      Dict[str, Any],
        output_dir:     Optional[str],
        metrics:        ICICIProcessingMetrics,
        pipeline_start: float,
    ) -> ICICIProcessingResult:
        """Full HDFC-style pipeline with coordinate parser."""
        from .report_generator import generate_report

        self.logger.info("ICICI FREE MODE: full pipeline with coordinate parser")

        if output_dir is None:
            output_dir = os.path.dirname(file_path) or "."

        try:
            # =================================================================
            # STEP 1: Structure Validation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 1: ICICI Structure Validation")
            
            text_content = self.parser._extract_text(file_path)
            structure_result = self.structure_validator.validate(text_content)
            statement_metadata = structure_result.metadata
            
            metrics.step_timings["structure_validation"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Structure validation passed: account=%s", statement_metadata.account_number)

            # =================================================================
            # STEP 2: PDF Parsing
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 2: Transaction Parsing")
            
            parse_result = self.parser.parse(file_path, text_content=text_content)
            transactions = [txn.to_dict() for txn in parse_result.transactions]
            metrics.transaction_count = len(transactions)
            metrics.step_timings["parsing"] = round((time.monotonic() - step_start) * 1000, 1)
            
            self.logger.info("Parsed %d ICICI transactions", len(transactions))

            # =================================================================
            # STEP 3: Transaction Validation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 3: Transaction Validation")
            
            validation_result = self.transaction_validator.validate(transactions)
            transactions = validation_result.validated_transactions
            
            metrics.step_timings["transaction_validation"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Transaction validation: %d valid", len(transactions))

            # =================================================================
            # STEP 4: Balance Reconciliation with Auto-Correction
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 4: Balance Reconciliation")
            
            # Try auto-correction first
            transactions, corrections = self.reconciliation.auto_correct_debit_credit(transactions)
            metrics.corrections_made = corrections
            if corrections > 0:
                self.logger.info("Auto-corrected %d debit/credit assignments", corrections)
            
            try:
                recon_result = self.reconciliation.reconcile(
                    transactions,
                    expected_opening=statement_metadata.opening_balance,
                    expected_closing=statement_metadata.closing_balance,
                )
            except ICICIReconciliationError as e:
                if self.strict_mode:
                    raise ICICIProcessorError(
                        str(e), stage="reconciliation", error_code=e.error_code, details=e.details
                    )
                self.logger.warning("Reconciliation failed (non-strict mode): %s", str(e))
                recon_result = None
            
            metrics.reconciliation_passed = recon_result.is_reconciled if recon_result else False
            metrics.step_timings["reconciliation"] = round((time.monotonic() - step_start) * 1000, 1)

            # =================================================================
            # STEP 5: Rule Engine Classification
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 5: Rule Engine Classification")
            
            classified, unclassified = self.rule_engine.classify(transactions)
            
            metrics.classified_count = len(classified)
            metrics.step_timings["rule_engine"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Rule engine: %d classified, %d unclassified", len(classified), len(unclassified))

            # =================================================================
            # STEP 6: AI Fallback (if enabled)
            # =================================================================
            ai_classified_count = 0
            
            if self.enable_ai and unclassified:
                step_start = time.monotonic()
                self.logger.info("Step 6: AI Classification (%d transactions)", len(unclassified))
                
                ai_results, ai_stats = self.ai_fallback.classify(
                    unclassified,
                    bank_name="ICICI",
                    account_type=user_info.get("account_type", "Salaried"),
                )
                
                ai_classified_count = sum(1 for t in ai_results if not t.get("category", "").startswith("Others"))
                all_transactions = classified + ai_results
                metrics.ai_classified_count = ai_classified_count
                metrics.step_timings["ai_classification"] = round((time.monotonic() - step_start) * 1000, 1)
            else:
                # Tag unclassified as Others
                for txn in unclassified:
                    is_debit = txn.get("debit") is not None
                    txn["category"] = "Others Debit" if is_debit else "Others Credit"
                    txn["confidence"] = 0.5
                    txn["source"] = "default_others"
                
                all_transactions = classified + unclassified
            
            metrics.unclassified_count = sum(1 for t in all_transactions if t.get("category", "").startswith("Others"))

            # =================================================================
            # STEP 7: Recurring Detection
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 7: Recurring Detection")
            
            all_transactions = self.recurring_engine.detect(all_transactions)
            
            metrics.recurring_count = sum(1 for t in all_transactions if t.get("is_recurring"))
            metrics.step_timings["recurring_detection"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Detected %d recurring transactions", metrics.recurring_count)

            # =================================================================
            # STEP 8: Aggregation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 8: Aggregation")
            
            aggregation = self.aggregation_engine.aggregate(
                all_transactions,
                opening_balance=statement_metadata.opening_balance or 0,
                closing_balance=statement_metadata.closing_balance or 0,
            )
            
            metrics.step_timings["aggregation"] = round((time.monotonic() - step_start) * 1000, 1)

            # =================================================================
            # STEP 9: Compute Data Quality
            # =================================================================
            data_quality, recon_status, dq_warnings = compute_data_quality(
                recon_passed=metrics.reconciliation_passed,
                corrections=metrics.corrections_made,
                total=len(all_transactions),
                mismatches=len(recon_result.mismatches) if recon_result else 0,
            )

            # =================================================================
            # STEP 10: Generate Report
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 10: Report Generation")
            
            excel_filename = f"icici_report_{uuid.uuid4().hex[:12]}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)

            report_stats = generate_report(
                transactions=all_transactions,
                output_path=excel_path,
                user_info=user_info,
            )

            metrics.step_timings["report_generation"] = round((time.monotonic() - step_start) * 1000, 1)
            metrics.total_time_ms = round((time.monotonic() - pipeline_start) * 1000, 1)

            self.logger.info(
                "ICICI FREE MODE complete: %d transactions, %d recurring, %.1fms, reconciled=%s",
                len(all_transactions),
                metrics.recurring_count,
                metrics.total_time_ms,
                metrics.reconciliation_passed,
            )

            return ICICIProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=all_transactions,
                aggregation=aggregation,
                metrics=metrics,
                data_quality=data_quality.value,
                reconciliation_status=recon_status,
                data_quality_warnings=dq_warnings,
            )

        except ICICIProcessorError:
            raise
        except Exception as e:
            self.logger.error("ICICI processing failed: %s", str(e), exc_info=True)
            raise ICICIProcessorError(
                f"ICICI processing failed: {str(e)}",
                stage="free_mode",
                error_code="ICICI_PROCESSING_ERROR",
            )
