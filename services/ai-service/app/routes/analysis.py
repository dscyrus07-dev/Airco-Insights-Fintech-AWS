"""
AI analysis routes for AI Intelligence Service.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List

from ..models.ai import (
    AIAnalysisRequest, AIAnalysisResponse, 
    AnalysisType, AIProvider
)
from ..services.ai_processor import ai_processor
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_transactions(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze transactions using AI.
    
    Args:
        request: AI analysis request
        background_tasks: FastAPI background tasks
    
    Returns:
        AI analysis response with categorized transactions
    """
    try:
        logger.info("AI analysis request received", 
                   analysis_type=request.analysis_type.value,
                   transaction_count=len(request.transactions),
                   provider=request.provider.value if request.provider else "default")
        
        # Validate request
        if len(request.transactions) == 0:
            raise HTTPException(status_code=400, detail="No transactions provided")
        
        if len(request.transactions) > 100:
            raise HTTPException(status_code=400, detail="Too many transactions (max 100)")
        
        # Process analysis
        result = await ai_processor.analyze_transactions(request)
        
        # If processing is async, add to background tasks
        if result.status == "processing":
            background_tasks.add_task(
                _complete_analysis,
                result.analysis_id
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI analysis request failed", error=str(e))
        raise HTTPException(status_code=500, detail="AI analysis failed")

@router.get("/analyze/{analysis_id}", response_model=AIAnalysisResponse)
async def get_analysis_result(analysis_id: str):
    """
    Get AI analysis result by ID.
    
    Args:
        analysis_id: Analysis ID
    
    Returns:
        AI analysis result
    """
    try:
        result = await ai_processor.get_analysis_result(analysis_id)
        if not result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis result", 
                    analysis_id=analysis_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analysis result")

@router.get("/categories", response_model=List[str])
async def get_supported_categories():
    """
    Get list of supported transaction categories.
    
    Returns:
        List of supported categories
    """
    try:
        categories = await ai_processor.get_supported_categories()
        return categories
        
    except Exception as e:
        logger.error("Failed to get supported categories", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported categories")

@router.post("/feedback")
async def submit_feedback(feedback: dict):
    """
    Submit learning feedback for AI improvement.
    
    Args:
        feedback: Feedback data
    
    Returns:
        Feedback submission result
    """
    try:
        success = await ai_processor.submit_feedback(feedback)
        
        if success:
            return {"message": "Feedback submitted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit feedback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/providers")
async def get_supported_providers():
    """
    Get list of supported AI providers.
    
    Returns:
        List of supported AI providers
    """
    return [
        {
            "name": AIProvider.GROQ.value,
            "description": "Groq - Fast inference",
            "available": bool(ai_processor.groq_client.api_key)
        },
        {
            "name": AIProvider.CLAUDE.value,
            "description": "Claude - Advanced analysis",
            "available": bool(ai_processor.claude_client.api_key)
        }
    ]

@router.get("/health/detailed")
async def detailed_health():
    """
    Get detailed health status including AI provider availability.
    
    Returns:
        Detailed health status
    """
    return {
        "status": "ok",
        "service": "ai-service",
        "version": "1.0.0",
        "providers": {
            "groq": {
                "available": bool(ai_processor.groq_client.api_key),
                "model": ai_processor.groq_client.model
            },
            "claude": {
                "available": bool(ai_processor.claude_client.api_key),
                "model": ai_processor.claude_client.model
            }
        }
    }

async def _complete_analysis(analysis_id: str):
    """Background task to complete analysis."""
    # This would be used for async processing
    # For now, processing is synchronous
    pass
