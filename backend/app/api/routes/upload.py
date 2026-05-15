"""
API endpoints for PDF upload and Excel conversion.
Supports dynamic bank engine selection: HDFC | Axis | ICICI | Kotak | SBI

Each bank uses its own dedicated parser, classifier, and report generator.
No AI. No fuzzy logic. Fully deterministic, bank-specific processing.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
import tempfile
import os
import logging
from pathlib import Path
from typing import Optional

from ...dependencies.auth import get_current_user, require_user_role
from ...utils.logging import get_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# ── Bank engine registry ───────────────────────────────────────────────────────
# Maps bank_name (lowercase, normalized) → (parser_factory, report_generator_fn, prefix)

def _get_bank_engine(bank_name: str):
    """
    Return (parse_fn, generate_report_fn, file_prefix) for the requested bank.

    parse_fn(file_path) → parse_result with .transactions list and .to_dict() on each
    generate_report_fn(transactions, output_path, user_info) → stats dict
    """
    key = bank_name.lower().strip().replace(" ", "").replace("_", "").replace("-", "")

    if key in ("hdfc", "hdfcbank"):
        from ...services.banks.hdfc.parser import HDFCParser
        from ...services.banks.hdfc.report_generator import generate_report
        return HDFCParser(), generate_report, "hdfc"

    if key in ("axis", "axisbank"):
        from ...services.banks.axis.parser import AxisParser
        from ...services.banks.axis.report_generator import generate_report
        return AxisParser(), generate_report, "axis"

    if key in ("icici", "icicibank"):
        from ...services.banks.icici.parser import ICICIParser
        from ...services.banks.icici.report_generator import generate_report
        return ICICIParser(), generate_report, "icici"

    if key in ("kotak", "kotakbank", "kotakmahindrabank"):
        from ...services.banks.kotak.parser import KotakParser
        from ...services.banks.kotak.report_generator import generate_report
        return KotakParser(), generate_report, "kotak"

    if key in ("sbi", "sbibank", "statebankofindia", "statebank"):
        from ...services.banks.sbi.parser import SBIParser
        from ...services.banks.sbi.report_generator import generate_report
        return SBIParser(), generate_report, "sbi"

    if key in ("canara", "canarabank"):
        from ...services.banks.canara.parser import CanaraParser
        from ...services.banks.canara.report_generator import generate_report
        return CanaraParser(), generate_report, "canara"

    if key in ("idfc", "idfcbank", "idfcfirst", "idfcfirstbank"):
        from ...services.banks.idfc.parser import IDFCParser
        from ...services.banks.idfc.report_generator import generate_report
        return IDFCParser(), generate_report, "idfc"

    if key in ("karnataka", "karnatakabank"):
        from ...services.banks.karnataka.parser import KarnatakaParser
        from ...services.banks.karnataka.report_generator import generate_report
        return KarnatakaParser(), generate_report, "karnataka"

    if key in ("paytm", "paytmbank", "paytmpaymentsbank"):
        from ...services.banks.paytm.parser import PaytmParser
        from ...services.banks.paytm.report_generator import generate_report
        return PaytmParser(), generate_report, "paytm"

    if key in ("union", "unionbank", "unionbankofindia", "ubi"):
        from ...services.banks.union.parser import UnionParser
        from ...services.banks.union.report_generator import generate_report
        return UnionParser(), generate_report, "union"

    if key in ("bankofbaroda", "bankofbaroda", "bob", "baroda"):
        from ...services.banks.bank_of_baroda.parser import BankOfBarodaParser
        from ...services.banks.bank_of_baroda.report_generator import generate_report
        return BankOfBarodaParser(), generate_report, "bank_of_baroda"

    if key in ("unknown", "unknownbank"):
        from ...services.banks.unknown.parser import UnknownParser
        from ...services.banks.unknown.report_generator import generate_report
        return UnknownParser(), generate_report, "unknown"

    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported bank: '{bank_name}'. "
            "Supported banks: HDFC, Axis, ICICI, Kotak, SBI, Canara, IDFC, Karnataka, Paytm, Union, Bank of Baroda, Unknown"
        )
    )


async def _process_bank_pdf(
    file: UploadFile,
    bank_name: str,
    user_info: dict,
) -> FileResponse:
    """
    Core processing pipeline for any bank PDF upload.
    1. Save PDF to temp file
    2. Select bank engine
    3. Parse → generate 5-sheet Excel
    4. Return FileResponse
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as pdf_temp:
        pdf_temp.write(content)
        pdf_path = pdf_temp.name

    excel_path = None

    try:
        parser, generate_report, prefix = _get_bank_engine(bank_name)

        logger.info("Processing %s PDF: %s (%d bytes)", bank_name.upper(), file.filename, len(content))

        # Step 1: Parse
        result       = parser.parse(pdf_path)
        transactions = [txn.to_dict() for txn in result.transactions]

        logger.info("%s: parsed %d transactions", bank_name.upper(), len(transactions))

        # Step 2: Generate 5-sheet report
        excel_path   = pdf_path.replace('.pdf', f'_{prefix}_report.xlsx')
        report_stats = generate_report(
            transactions=transactions,
            output_path=excel_path,
            user_info=user_info,
        )

        logger.info(
            "%s: report ready — %d txns, %d categories, %d recurring",
            bank_name.upper(),
            report_stats.get("total_transactions", 0),
            report_stats.get("categories_used", 0),
            report_stats.get("recurring_count", 0),
        )

        output_filename = f"{Path(file.filename).stem}_{prefix}_report.xlsx"
        return FileResponse(
            excel_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=output_filename,
            headers={"Content-Disposition": f"attachment; filename={output_filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing %s PDF: %s", bank_name.upper(), str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

    finally:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except Exception as cleanup_err:
            logger.warning("Cleanup error: %s", str(cleanup_err))


# ── Universal multi-bank endpoint ─────────────────────────────────────────────

@router.post("/bank-statement")
async def upload_bank_statement(
    file:         UploadFile = File(...),
    bank_name:    str        = Form(...),
    full_name:    str        = Form(default=""),
    account_type: str        = Form(default=""),
    current_user: dict       = Depends(require_user_role),
):
    """
    Universal bank statement upload endpoint.
    Accepts any supported bank PDF and returns a 5-sheet categorized Excel report.

    Form fields:
      - file:         PDF file (required)
      - bank_name:    "HDFC" | "Axis" | "ICICI" | "Kotak"  (required)
      - full_name:    Account holder name  (optional)
      - account_type: "Salaried" | "Business"  (optional)

    Returns: Excel file (.xlsx) with 5 sheets:
      Summary | Category Analysis | Weekly Analysis | Recurring | Raw Transactions
    """
    user_info = {
        "full_name":    full_name or current_user.get("name", ""),
        "account_type": account_type,
        "bank_name":    bank_name,
        "user_id":      current_user.get("id"),
        "email":        current_user.get("email"),
    }
    
    logger.info(
        "Processing upload for user %s (%s) - bank: %s, file: %s",
        current_user.get("id"),
        current_user.get("email"),
        bank_name,
        file.filename
    )
    
    return await _process_bank_pdf(file, bank_name, user_info)


# ── Legacy bank-specific endpoints (backward compatibility) ───────────────────

@router.post("/hdfc-pdf")
async def upload_hdfc_pdf(
    file:         UploadFile = File(...),
    full_name:    str        = Form(default=""),
    account_type: str        = Form(default=""),
    current_user: dict       = Depends(require_user_role),
):
    """Legacy HDFC-specific endpoint. Prefer /bank-statement."""
    user_info = {
        "full_name":    full_name or current_user.get("name", ""),
        "account_type": account_type,
        "bank_name":    "HDFC",
        "user_id":      current_user.get("id"),
        "email":        current_user.get("email"),
    }
    return await _process_bank_pdf(file, "hdfc", user_info)


@router.post("/axis-pdf")
async def upload_axis_pdf(
    file:         UploadFile = File(...),
    full_name:    str        = Form(default=""),
    account_type: str        = Form(default=""),
    current_user: dict       = Depends(require_user_role),
):
    """Axis Bank statement upload."""
    user_info = {
        "full_name":    full_name or current_user.get("name", ""),
        "account_type": account_type,
        "bank_name":    "Axis Bank",
        "user_id":      current_user.get("id"),
        "email":        current_user.get("email"),
    }
    return await _process_bank_pdf(file, "axis", user_info)


@router.post("/icici-pdf")
async def upload_icici_pdf(
    file:         UploadFile = File(...),
    full_name:    str        = Form(default=""),
    account_type: str        = Form(default=""),
    current_user: dict       = Depends(require_user_role),
):
    """ICICI Bank statement upload."""
    user_info = {
        "full_name":    full_name or current_user.get("name", ""),
        "account_type": account_type,
        "bank_name":    "ICICI Bank",
        "user_id":      current_user.get("id"),
        "email":        current_user.get("email"),
    }
    return await _process_bank_pdf(file, "icici", user_info)


@router.post("/kotak-pdf")
async def upload_kotak_pdf(
    file:         UploadFile = File(...),
    full_name:    str        = Form(default=""),
    account_type: str        = Form(default=""),
    current_user: dict       = Depends(require_user_role),
):
    """Kotak Bank statement upload."""
    user_info = {
        "full_name":    full_name or current_user.get("name", ""),
        "account_type": account_type,
        "bank_name":    "Kotak Bank",
        "user_id":      current_user.get("id"),
        "email":        current_user.get("email"),
    }
    return await _process_bank_pdf(file, "kotak", user_info)
