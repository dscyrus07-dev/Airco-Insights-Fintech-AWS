"""
PDF processing models for PDF Processing Service.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BankType(str, Enum):
    HDFC = "hdfc"
    AXIS = "axis"
    ICICI = "icici"
    KOTAK = "kotak"
    SBI = "sbi"

class Transaction(BaseModel):
    """Transaction model."""
    date: str = Field(..., description="Transaction date")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    type: str = Field(..., description="Credit/Debit")
    balance: Optional[float] = Field(None, description="Account balance")
    category: Optional[str] = Field(None, description="Transaction category")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PDFProcessingRequest(BaseModel):
    """PDF processing request model."""
    file_id: str = Field(..., description="File ID from File Service")
    file_url: str = Field(..., description="File URL from storage")
    bank_name: BankType = Field(..., description="Bank type")
    user_id: Optional[str] = Field(None, description="User ID")
    processing_options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")

class PDFProcessingResponse(BaseModel):
    """PDF processing response model."""
    processing_id: str
    file_id: str
    status: ProcessingStatus
    transactions: List[Transaction] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PDFProcessingEvent(BaseModel):
    """PDF processing event model."""
    event_type: str
    processing_id: str
    file_id: str
    bank_name: BankType
    status: ProcessingStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProcessingSummary(BaseModel):
    """Processing summary model."""
    total_transactions: int
    total_credits: int
    total_debits: int
    total_amount: float
    date_range: Dict[str, str]
    categories: Dict[str, int]
    processing_time_seconds: float
    confidence_score: Optional[float] = None
