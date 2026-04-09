"""
Claude AI client for transaction analysis.
"""

import json
from typing import Dict, Any, List
import httpx

from ..config import settings
from ..models.ai import AnalysisType, TransactionAnalysis
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ClaudeClient:
    """Claude AI client."""
    
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.base_url = "https://api.anthropic.com/v1"
    
    async def analyze_transactions(self, transactions: List[Dict[str, Any]], analysis_type: AnalysisType, options: Dict[str, Any]) -> List[TransactionAnalysis]:
        """Analyze transactions using Claude AI."""
        if not self.api_key:
            raise ValueError("Claude API key not configured")
        
        try:
            # Prepare prompt based on analysis type
            prompt = self._build_prompt(transactions, analysis_type, options)
            
            # Call Claude API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 4000,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                )
                
                if response.status_code != 200:
                    logger.error("Claude API error", status=response.status_code, text=response.text)
                    raise Exception(f"Claude API error: {response.status_code}")
                
                result = response.json()
                
                # Parse response
                return self._parse_response(result, transactions)
                
        except Exception as e:
            logger.error("Claude analysis failed", error=str(e))
            raise
    
    def _build_prompt(self, transactions: List[Dict[str, Any]], analysis_type: AnalysisType, options: Dict[str, Any]) -> str:
        """Build prompt for AI analysis."""
        # Limit transactions to avoid token limits
        limited_transactions = transactions[:25]
        
        prompt = f"""You are a financial transaction analysis expert. Analyze the following {len(limited_transactions)} transactions and provide {analysis_type.value}.

Transactions:
"""
        
        for i, txn in enumerate(limited_transactions, 1):
            prompt += f"{i}. Date: {txn.get('date', 'N/A')}\n"
            prompt += f"   Description: {txn.get('description', 'N/A')}\n"
            prompt += f"   Amount: {txn.get('amount', 'N/A')}\n"
            prompt += f"   Type: {txn.get('type', 'N/A')}\n\n"
        
        prompt += f"""
Categories to use: Food & Dining, Shopping, Transportation, Bills & Utilities, Entertainment, Healthcare, Education, Travel, Investments, Income, Transfers, Others.

Please provide analysis for each transaction in JSON format:
```json
[
  {{
    "category": "predicted_category",
    "confidence": 0.85,
    "subcategory": "optional_subcategory",
    "tags": ["tag1", "tag2"],
    "insights": ["brief insight about the transaction"]
  }}
]
```

Focus on accuracy and provide confidence scores based on how certain you are about the categorization."""
        
        return prompt
    
    def _parse_response(self, result: Dict[str, Any], transactions: List[Dict[str, Any]]) -> List[TransactionAnalysis]:
        """Parse AI response into TransactionAnalysis objects."""
        try:
            content = result["content"][0]["text"]
            
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            
            if json_match:
                json_content = json_match.group(1)
                analysis_data = json.loads(json_content)
                
                if isinstance(analysis_data, list):
                    return self._convert_to_analysis_objects(analysis_data, transactions)
            
        except Exception as e:
            logger.error("Failed to parse Claude response", error=str(e))
        
        # Fallback to keyword-based categorization
        return self._extract_from_text(content, transactions)
    
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
