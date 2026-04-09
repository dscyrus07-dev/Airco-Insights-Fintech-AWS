"""
Groq AI client for transaction analysis.
"""

import json
from typing import Dict, Any, List
import httpx

from ..config import settings
from ..models.ai import AnalysisType, TransactionAnalysis
from ..utils.logging import get_logger

logger = get_logger(__name__)

class GroqClient:
    """Groq AI client."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def analyze_transactions(self, transactions: List[Dict[str, Any]], analysis_type: AnalysisType, options: Dict[str, Any]) -> List[TransactionAnalysis]:
        """Analyze transactions using Groq AI."""
        if not self.api_key:
            raise ValueError("Groq API key not configured")
        
        try:
            # Prepare prompt based on analysis type
            prompt = self._build_prompt(transactions, analysis_type, options)
            
            # Call Groq API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": self._get_system_prompt(analysis_type)
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code != 200:
                    logger.error("Groq API error", status=response.status_code, text=response.text)
                    raise Exception(f"Groq API error: {response.status_code}")
                
                result = response.json()
                
                # Parse response
                return self._parse_response(result, transactions)
                
        except Exception as e:
            logger.error("Groq analysis failed", error=str(e))
            raise
    
    def _get_system_prompt(self, analysis_type: AnalysisType) -> str:
        """Get system prompt for analysis type."""
        if analysis_type == AnalysisType.CATEGORIZATION:
            return """You are a financial transaction categorization expert. 
            Analyze the provided transactions and categorize them accurately.
            
            Categories to use: Food & Dining, Shopping, Transportation, Bills & Utilities, 
            Entertainment, Healthcare, Education, Travel, Investments, Income, Transfers, Others.
            
            Return results as JSON array with objects containing:
            - category: predicted category
            - confidence: confidence score (0-1)
            - subcategory: optional subcategory
            - tags: relevant tags
            - insights: brief insights"""
        
        elif analysis_type == AnalysisType.ENRICHMENT:
            return """You are a financial data enrichment expert.
            Enrich transactions with additional context and insights.
            
            Return results as JSON array with enhanced transaction information."""
        
        else:
            return "You are a financial analysis expert. Analyze the provided transactions."
    
    def _build_prompt(self, transactions: List[Dict[str, Any]], analysis_type: AnalysisType, options: Dict[str, Any]) -> str:
        """Build prompt for AI analysis."""
        # Limit transactions to avoid token limits
        limited_transactions = transactions[:25]
        
        prompt = f"Analyze the following {len(limited_transactions)} transactions:\n\n"
        
        for i, txn in enumerate(limited_transactions, 1):
            prompt += f"{i}. Date: {txn.get('date', 'N/A')}\n"
            prompt += f"   Description: {txn.get('description', 'N/A')}\n"
            prompt += f"   Amount: {txn.get('amount', 'N/A')}\n"
            prompt += f"   Type: {txn.get('type', 'N/A')}\n"
            prompt += "\n"
        
        prompt += f"\nProvide {analysis_type.value} analysis for each transaction."
        
        if options:
            prompt += f"\nAdditional options: {json.dumps(options)}"
        
        return prompt
    
    def _parse_response(self, result: Dict[str, Any], transactions: List[Dict[str, Any]]) -> List[TransactionAnalysis]:
        """Parse AI response into TransactionAnalysis objects."""
        try:
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            try:
                analysis_data = json.loads(content)
                if isinstance(analysis_data, list):
                    return self._convert_to_analysis_objects(analysis_data, transactions)
            except json.JSONDecodeError:
                # If not JSON, try to extract structured data
                return self._extract_from_text(content, transactions)
            
        except Exception as e:
            logger.error("Failed to parse Groq response", error=str(e))
            # Return empty analysis with error
            return []
    
    def _convert_to_analysis_objects(self, analysis_data: List[Dict], transactions: List[Dict[str, Any]]) -> List[TransactionAnalysis]:
        """Convert parsed data to TransactionAnalysis objects."""
        results = []
        
        for i, data in enumerate(analysis_data):
            if i < len(transactions):
                txn = transactions[i]
                
                result = TransactionAnalysis(
                    transaction_id=txn.get('id'),
                    category=data.get('category', 'Others'),
                    confidence=float(data.get('confidence', 0.5)),
                    subcategory=data.get('subcategory'),
                    tags=data.get('tags', []),
                    insights=data.get('insights', []),
                    metadata=data.get('metadata', {})
                )
                results.append(result)
        
        return results
    
    def _extract_from_text(self, content: str, transactions: List[Dict[str, Any]]) -> List[TransactionAnalysis]:
        """Extract analysis from text response."""
        # Fallback parsing for non-JSON responses
        results = []
        
        for i, txn in enumerate(transactions):
            # Simple categorization based on keywords
            description = txn.get('description', '').lower()
            category = self._categorize_by_keywords(description)
            
            result = TransactionAnalysis(
                transaction_id=txn.get('id'),
                category=category,
                confidence=0.6,  # Lower confidence for keyword-based
                tags=[],
                insights=[]
            )
            results.append(result)
        
        return results
    
    def _categorize_by_keywords(self, description: str) -> str:
        """Categorize transaction based on keywords."""
        keywords = {
            "Food & Dining": ["restaurant", "food", "cafe", "dining", "pizza", "burger", "swiggy", "zomato"],
            "Shopping": ["amazon", "flipkart", "myntra", "store", "shop", "mall", "purchase"],
            "Transportation": ["uber", "ola", "taxi", "metro", "bus", "petrol", "diesel", "fuel"],
            "Bills & Utilities": ["electricity", "water", "gas", "phone", "internet", "recharge", "bill"],
            "Entertainment": ["movie", "netflix", "prime", "spotify", "game", "entertainment"],
            "Healthcare": ["hospital", "doctor", "medicine", "pharmacy", "health"],
            "Education": ["school", "college", "tuition", "course", "education"],
            "Travel": ["hotel", "flight", "train", "booking", "travel"],
            "Investments": ["sip", "mutual fund", "stock", "investment", "interest"],
            "Income": ["salary", "income", "credit", "deposit"],
            "Transfers": ["transfer", "neft", "rtgs", "imps", "send"]
        }
        
        for category, category_keywords in keywords.items():
            for keyword in category_keywords:
                if keyword in description:
                    return category
        
        return "Others"
