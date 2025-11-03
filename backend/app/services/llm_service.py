import logging
from typing import List, Tuple
import requests
import warnings
import urllib3
from app.core.config import settings

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        logger.info("Initializing Groq LLM Service")
        self.api_url = settings.GROQ_API_URL
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL if hasattr(settings, 'GROQ_MODEL') else "llama-3.1-8b-instant"
        
    def generate_response(self, query: str, context: List[Tuple[str, float]]) -> str:
        """Generate responses using Groq API with RAG context"""
        
        if not context:
            return "I couldn't find specific information about your question in our HR documents. Please contact the HR department directly for assistance, or try rephrasing your question."
        
        # Build prompt with context
        prompt = self._build_prompt(query, context)
        
        # Call Groq API
        response = self._call_grok_api(prompt)
        
        logger.info("Generated response successfully using Groq")
        return response

    def _build_prompt(self, query: str, context: List[Tuple[str, float]]) -> str:
        """Build prompt with context for Groq API"""
        
        # Extract top context documents
        context_texts = [doc[0] for doc in context[:3]]
        context_str = "\n\n".join(context_texts)
        
        prompt = f"""You are an HR assistant. Answer the user's question based ONLY on the provided HR documents context. 
If the information is not in the context, politely say you don't have that specific information in the HR documents.

HR Documents Context:
{context_str}

User Question: {query}

Please provide a helpful, accurate response based only on the HR documents above:"""
        
        return prompt

    def _call_grok_api(self, prompt: str) -> str:
        """Call Groq API to generate response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": self.model,
                "max_tokens": 1024,
                "temperature": 0.1,
                "top_p": 0.9,
                "stream": False
            }
            
            logger.info(f"Sending request to Groq API with prompt length: {len(prompt)}")
            
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload, 
                timeout=60,
                verify=False
            )
            
            logger.info(f"Groq API Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['choices'][0]['message']['content'].strip()
                logger.info(f"Groq API Response received ({len(response_text)} characters)")
                return response_text
            else:
                error_msg = f"Groq API call failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return "I apologize, but I'm having trouble processing your request at the moment. Please try again later."
                
        except requests.exceptions.Timeout:
            logger.error("Groq API request timed out")
            return "I apologize, but the request is taking longer than expected. Please try again later."
        except requests.exceptions.ConnectionError:
            logger.error("Groq API connection error")
            return "I apologize, but I'm unable to connect to the service at the moment. Please try again later."
        except Exception as e:
            logger.error(f"Groq API call error: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."

    def classify_query(self, query: str) -> str:
        """Classify query into HR categories"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['leave', 'vacation', 'holiday', 'sick', 'time off']):
            return "leave"
        elif any(word in query_lower for word in ['policy', 'rule', 'guideline', 'procedure']):
            return "policy"
        elif any(word in query_lower for word in ['remote', 'work from home', 'wfh']):
            return "remote work"
        elif any(word in query_lower for word in ['benefit', 'insurance', 'health', 'retirement']):
            return "benefits"
        elif any(word in query_lower for word in ['salary', 'pay', 'compensation']):
            return "compensation"
        elif any(word in query_lower for word in ['onboard', 'training', 'new employee']):
            return "onboarding"
        elif any(word in query_lower for word in ['dress', 'code', 'attire', 'clothing']):
            return "dress code"
        else:
            return "general"