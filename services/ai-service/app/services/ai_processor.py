"""
AI processing service for transaction analysis and categorization.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..models.ai import (
    AIAnalysisRequest, AIAnalysisResponse, 
    AnalysisType, AIProvider, TransactionAnalysis,
    AnalysisSummary
)
from ..services.groq_client import GroqClient
from ..services.claude_client import ClaudeClient
from ..utils.logging import get_logger

logger = get_logger(__name__)

class AIProcessor:
    """AI processing service."""
    
    def __init__(self):
        self.groq_client = GroqClient()
        self.claude_client = ClaudeClient()
        self._analysis_cache: Dict[str, AIAnalysisResponse] = {}
    
    async def analyze_transactions(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """Analyze transactions using AI."""
        analysis_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info("Starting AI analysis", 
                   analysis_id=analysis_id,
                   analysis_type=request.analysis_type.value,
                   transaction_count=len(request.transactions))
        
        try:
            # Create analysis response
            response = AIAnalysisResponse(
                analysis_id=analysis_id,
                analysis_type=request.analysis_type,
                provider=request.provider or AIProvider.GROQ,
                status="processing"
            )
            
            # Select AI provider
            provider = request.provider or AIProvider.GROQ
            client = self._get_client(provider)
            
            # Process transactions in batches
            batch_size = 25  # Process in batches to avoid rate limits
            results = []
            errors = []
            
            for i in range(0, len(request.transactions), batch_size):
                batch = request.transactions[i:i + batch_size]
                
                try:
                    batch_results = await client.analyze_transactions(
                        batch, 
                        request.analysis_type,
                        request.options
                    )
                    results.extend(batch_results)
                    
                except Exception as e:
                    error_msg = f"Error processing batch {i//batch_size + 1}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Generate summary
            summary = self._generate_summary(results, processing_time, provider)
            
            # Update response
            response.status = "completed"
            response.results = results
            response.summary = summary
            response.processing_time_seconds = processing_time
            response.errors = errors
            
            logger.info("AI analysis completed successfully",
                       analysis_id=analysis_id,
                       result_count=len(results),
                       processing_time=processing_time)
            
            # Cache result
            self._analysis_cache[analysis_id] = response
            
            return response
            
        except Exception as e:
            logger.error("AI analysis failed",
                        analysis_id=analysis_id,
                        error=str(e))
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            response.status = "failed"
            response.errors.append(str(e))
            response.processing_time_seconds = processing_time
            
            return response
    
    def _get_client(self, provider: AIProvider):
        """Get AI client based on provider."""
        if provider == AIProvider.GROQ:
            return self.groq_client
        elif provider == AIProvider.CLAUDE:
            return self.claude_client
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def _generate_summary(self, results: List[TransactionAnalysis], processing_time: float, provider: AIProvider) -> Dict[str, Any]:
        """Generate analysis summary."""
        if not results:
            return {
                "total_transactions": 0,
                "categorized_transactions": 0,
                "uncategorized_transactions": 0,
                "category_distribution": {},
                "confidence_distribution": {},
                "processing_time_seconds": processing_time,
                "provider_used": provider.value,
                "model_version": "1.0.0"
            }
        
        total_transactions = len(results)
        categorized = len([r for r in results if r.category and r.category.lower() != "uncategorized"])
        uncategorized = total_transactions - categorized
        
        # Category distribution
        category_dist = {}
        for result in results:
            cat = result.category
            category_dist[cat] = category_dist.get(cat, 0) + 1
        
        # Confidence distribution
        confidence_dist = {}
        for result in results:
            conf_range = self._get_confidence_range(result.confidence)
            confidence_dist[conf_range] = confidence_dist.get(conf_range, 0) + 1
        
        return {
            "total_transactions": total_transactions,
            "categorized_transactions": categorized,
            "uncategorized_transactions": uncategorized,
            "category_distribution": category_dist,
            "confidence_distribution": confidence_dist,
            "processing_time_seconds": processing_time,
            "provider_used": provider.value,
            "model_version": "1.0.0"
        }
    
    def _get_confidence_range(self, confidence: float) -> str:
        """Get confidence range label."""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        elif confidence >= 0.4:
            return "low"
        else:
            return "very_low"
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[AIAnalysisResponse]:
        """Get analysis result by ID."""
        return self._analysis_cache.get(analysis_id)
    
    async def submit_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Submit learning feedback."""
        try:
            # This would store feedback for learning
            # For now, just log it
            logger.info("Learning feedback submitted", feedback=feedback)
            return True
        except Exception as e:
            logger.error("Failed to submit feedback", error=str(e))
            return False
    
    async def get_supported_categories(self) -> List[str]:
        """Get list of supported categories."""
        from ..config import settings
        return settings.DEFAULT_CATEGORIES

# Global AI processor instance
ai_processor = AIProcessor()
