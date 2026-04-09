"""
Report generation models for Report Generation Service.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class ReportFormat(str, Enum):
    EXCEL = "excel"
    PDF = "pdf"
    CSV = "csv"

class ReportType(str, Enum):
    STANDARD = "standard"
    DETAILED = "detailed"
    SUMMARY = "summary"
    CUSTOM = "custom"

class Transaction(BaseModel):
    """Transaction model for report generation."""
    date: str = Field(..., description="Transaction date")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    type: str = Field(..., description="Credit/Debit")
    balance: Optional[float] = Field(None, description="Account balance")
    category: Optional[str] = Field(None, description="Transaction category")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    confidence: Optional[float] = Field(None, description="AI confidence score")
    tags: List[str] = Field(default_factory=list, description="Transaction tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ReportGenerationRequest(BaseModel):
    """Report generation request model."""
    file_id: str = Field(..., description="Source file ID")
    transactions: List[Transaction] = Field(..., description="List of transactions")
    bank_name: str = Field(..., description="Bank name")
    report_type: ReportType = Field(default=ReportType.STANDARD)
    report_format: ReportFormat = Field(default=ReportFormat.EXCEL)
    user_info: Dict[str, Any] = Field(default_factory=dict, description="User information")
    ai_results: Optional[Dict[str, Any]] = Field(None, description="AI analysis results")
    options: Dict[str, Any] = Field(default_factory=dict, description="Report options")

class ReportGenerationResponse(BaseModel):
    """Report generation response model."""
    report_id: str
    file_id: str
    status: ReportStatus
    report_url: Optional[str] = None
    download_url: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    processing_time_seconds: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportSummary(BaseModel):
    """Report summary model."""
    total_transactions: int
    total_credits: int
    total_debits: int
    total_amount: float
    date_range: Dict[str, str]
    categories: Dict[str, int]
    monthly_totals: Dict[str, float]
    average_transaction: float
    largest_transaction: Dict[str, Any]
    processing_time_seconds: float

class ReportTemplate(BaseModel):
    """Report template model."""
    name: str
    description: str
    sheets: List[str]
    bank_specific: bool = False
    bank_names: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
