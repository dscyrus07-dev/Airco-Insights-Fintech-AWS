"""
AI analysis models for AI Intelligence Service.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class AnalysisType(str, Enum):
    CATEGORIZATION = "categorization"
    ENRICHMENT = "enrichment"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTION = "prediction"
    INSIGHTS = "insights"

class AIProvider(str, Enum):
    GROQ = "groq"
    CLAUDE = "claude"
    OPENAI = "openai"
    LOCAL = "local"

class TransactionAnalysis(BaseModel):
    """Transaction analysis result."""
    transaction_id: Optional[str] = Field(None, description="Transaction ID")
    category: str = Field(..., description="Predicted category")
    confidence: float = Field(..., description="Confidence score (0-1)")
    subcategory: Optional[str] = Field(None, description="Subcategory if applicable")
    tags: List[str] = Field(default_factory=list, description="Transaction tags")
    insights: List[str] = Field(default_factory=list, description="AI insights")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AIAnalysisRequest(BaseModel):
    """AI analysis request model."""
    transactions: List[Dict[str, Any]] = Field(..., description="List of transactions to analyze")
    analysis_type: AnalysisType = Field(default=AnalysisType.CATEGORIZATION)
    provider: Optional[AIProvider] = Field(None, description="AI provider to use")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")
    file_id: Optional[str] = Field(None, description="Source file ID")
    user_id: Optional[str] = Field(None, description="User ID")

class AIAnalysisResponse(BaseModel):
    """AI analysis response model."""
    analysis_id: str
    analysis_type: AnalysisType
    provider: AIProvider
    status: str
    results: List[TransactionAnalysis]
    summary: Dict[str, Any] = Field(default_factory=dict)
    processing_time_seconds: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryMapping(BaseModel):
    """Category mapping model."""
    original: str = Field(..., description="Original category")
    mapped: str = Field(..., description="Mapped category")
    confidence: float = Field(..., description="Mapping confidence")
    examples: List[str] = Field(default_factory=list, description="Example descriptions")

class LearningFeedback(BaseModel):
    """Learning feedback model."""
    transaction_id: str
    original_category: str
    corrected_category: str
    user_id: Optional[str] = None
    feedback_type: str = Field(default="correction")
    notes: Optional[str] = None

class AnalysisSummary(BaseModel):
    """Analysis summary model."""
    total_transactions: int
    categorized_transactions: int
    uncategorized_transactions: int
    category_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    processing_time_seconds: float
    provider_used: AIProvider
    model_version: str
