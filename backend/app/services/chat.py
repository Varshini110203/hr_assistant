from app.core.database import get_chats_collection
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService
from app.models.chat import QueryResponse
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
        self.chats_collection = get_chats_collection()
        self.document_processor = get_document_processor()
        self.llm_service = get_llm_service()

    def process_query(self, user_id: str, chat_id: str, query: str) -> QueryResponse:
        """Process query within a continuous chat context"""
        if not self.document_processor or not self.document_processor.is_initialized():
            return QueryResponse(
                response="System not ready. Please try again shortly.",
                source_document="system",
                confidence=0.0
            )

        try:
            similar_docs = self.document_processor.search_similar(query)
            response_text = self.llm_service.generate_response(
                query, similar_docs, self.document_processor.get_version_context()
            )

            # Save message to existing chat or create new one
            message_data = {
                "role": "user",
                "content": query,
                "timestamp": datetime.utcnow()
            }
            assistant_message = {
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow()
            }

            if chat_id:
                # Append to existing chat
                self.chats_collection.update_one(
                    {"_id": ObjectId(chat_id), "user_id": ObjectId(user_id)},
                    {
                        "$push": {"messages": {"$each": [message_data, assistant_message]}},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
            else:
    # Create a new chat
                new_chat = {
                    "user_id": ObjectId(user_id),
                    "title": query[:40],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "messages": [message_data, assistant_message]
                }
                result = self.chats_collection.insert_one(new_chat)
                chat_id = str(result.inserted_id)

            return QueryResponse(
                response=response_text,
                source_document="document",
                confidence=similar_docs[0][1] if similar_docs else 0.0,
                chat_id=str(chat_id)
            )
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            return QueryResponse(
                response="I'm having trouble responding. Please try again later.",
                source_document="system",
                confidence=0.0
            )

    def get_chat_history(self, user_id: str):
        """Fetch all conversations for user"""
        chats = self.chats_collection.find({"user_id": ObjectId(user_id)}).sort("updated_at", -1)
        return [
            {
                "_id": str(chat["_id"]),
                "title": chat.get("title"),
                "created_at": chat["created_at"],
                "updated_at": chat["updated_at"],
                "messages": chat.get("messages", [])
            }
            for chat in chats
        ]

    def delete_chat(self, user_id: str, chat_id: str):
        """Delete specific chat"""
        result = self.chats_collection.delete_one({
            "_id": ObjectId(chat_id),
            "user_id": ObjectId(user_id)
        })
        return result.deleted_count > 0

    def clear_all_chats(self, user_id: str):
        """Clear all user chats"""
        result = self.chats_collection.delete_many({"user_id": ObjectId(user_id)})
        return result.deleted_count
