from app.core.database import get_messages_collection
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService
from app.models.chat import QueryResponse
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create singleton instances to avoid multiple initializations
_document_processor = None
_llm_service = None

def get_document_processor():
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
        _document_processor.initialize_vector_store()
    return _document_processor

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

class ChatService:
    def __init__(self):
        self.messages_collection = get_messages_collection()
        self.document_processor = get_document_processor()
        self.llm_service = get_llm_service()

    def process_query(self, user_id: str, query: str) -> QueryResponse:
        """Process user query using RAG pipeline (synchronous)"""
        
        # Check if vector store is initialized
        if not self.document_processor or not self.document_processor.is_initialized():
            logger.error("Document processor not initialized - vector store not ready")
            return QueryResponse(
                response="The document search system is not ready yet. Please try again in a moment.",
                source_document="system",
                confidence=0.0
            )
        
        try:
            # Search for similar documents
            similar_docs = self.document_processor.search_similar(query)
            logger.info(f"Found {len(similar_docs)} similar documents for query: {query}")
            
            if not similar_docs:
                return QueryResponse(
                    response="I couldn't find relevant information in our HR documents to answer your question. Please contact HR directly for assistance.",
                    source_document="none",
                    confidence=0.0
                )
            
            # Generate response using LLM
            response_text = self.llm_service.generate_response(query, similar_docs)
            
            # Classify query
            category = self.llm_service.classify_query(query)
            
            # Save to chat history
            message_id = self.save_message(user_id, query, response_text)
            
            return QueryResponse(
                response=response_text,
                source_document=category,
                confidence=similar_docs[0][1] if similar_docs else 0.0
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return QueryResponse(
                response="I apologize, but I'm having trouble processing your request right now. Please try again later.",
                source_document="system",
                confidence=0.0
            )

    def save_message(self, user_id: str, query: str, response: str) -> str:
        """Save chat message to database (synchronous) and return message ID"""
        try:
            if self.messages_collection is None:
                logger.error("Messages collection not available")
                return None
                
            message = {
                "user_id": ObjectId(user_id),
                "query": query,
                "response": response,
                "timestamp": datetime.utcnow()
            }
            
            result = self.messages_collection.insert_one(message)
            logger.info(f"Saved message for user {user_id} with ID {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    def get_chat_history(self, user_id: str, limit: int = 50) -> list:
        """Get user's chat history (synchronous)"""
        try:
            if self.messages_collection is None:
                logger.error("Messages collection not available")
                return []
                
            cursor = self.messages_collection.find(
                {"user_id": ObjectId(user_id)}
            ).sort("timestamp", -1).limit(limit)
            
            messages = []
            for doc in cursor:
                messages.append({
                    "_id": str(doc["_id"]),
                    "query": doc["query"],
                    "response": doc["response"],
                    "timestamp": doc["timestamp"]
                })
            
            return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return []

    def delete_message(self, user_id: str, message_id: str) -> bool:
        """Delete a specific message for a user"""
        try:
            if self.messages_collection is None:
                logger.error("Messages collection not available")
                return False
            
            # Validate the message_id format
            if not ObjectId.is_valid(message_id):
                logger.warning(f"Invalid message ID format: {message_id}")
                return False
                
            result = self.messages_collection.delete_one({
                "_id": ObjectId(message_id),
                "user_id": ObjectId(user_id)
            })
            
            if result.deleted_count > 0:
                logger.info(f"Deleted message {message_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Message {message_id} not found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            return False

    def clear_user_history(self, user_id: str) -> bool:
        """Clear all chat history for a user"""
        try:
            if self.messages_collection is None:
                logger.error("Messages collection not available")
                return False
                
            result = self.messages_collection.delete_many({
                "user_id": ObjectId(user_id)
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Cleared {deleted_count} messages for user {user_id}")
            
            # Return True even if no messages were found (considered successful)
            return True
            
        except Exception as e:
            logger.error(f"Error clearing user history: {str(e)}")
            return False