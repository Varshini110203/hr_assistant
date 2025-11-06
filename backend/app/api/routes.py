from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import UserCreate, User, Token
from app.models.chat import QueryRequest, QueryResponse
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.core.security import create_access_token
from app.api.dependencies import get_current_user
from datetime import timedelta
from app.core.config import settings

api_router = APIRouter()

@api_router.post("/register", response_model=User)
def register(user_data: UserCreate):
    auth_service = AuthService()
    try:
        user = auth_service.register_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@api_router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_service = AuthService()
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Store email in JWT token (this is what get_current_user expects)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/chat/query", response_model=QueryResponse)
def chat_query(request: QueryRequest, current_user: User = Depends(get_current_user)):
    chat_service = ChatService()
    chat_id = getattr(request, "chat_id", None)
    
    # Convert user ID to string for the chat service
    user_id_str = str(current_user.id)
    
    response = chat_service.process_query(user_id_str, chat_id, request.message)
    return response

@api_router.get("/chat/history")
def get_chat_history(current_user: User = Depends(get_current_user)):
    chat_service = ChatService()
    
    # Convert user ID to string for the chat service
    user_id_str = str(current_user.id)
    
    history = chat_service.get_chat_history(user_id_str)
    return history

@api_router.get("/chat/{chat_id}")
def get_chat(chat_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific chat by ID"""
    chat_service = ChatService()
    
    # Convert user ID to string for the chat service
    user_id_str = str(current_user.id)
    
    try:
        chat = chat_service.get_chat(user_id_str, chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        return chat
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat: {str(e)}"
        )

@api_router.delete("/chat/{chat_id}")
def delete_chat(chat_id: str, current_user: User = Depends(get_current_user)):
    """Delete an entire chat conversation"""
    chat_service = ChatService()
    
    # Convert user ID to string for the chat service
    user_id_str = str(current_user.id)
    
    try:
        success = chat_service.delete_chat(user_id_str, chat_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        return {"message": "Chat deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting chat: {str(e)}"
        )

@api_router.delete("/chat/history")
def clear_all_chat_history(current_user: User = Depends(get_current_user)):
    """Clear all chat conversations for the current user"""
    chat_service = ChatService()
    
    # Convert user ID to string for the chat service
    user_id_str = str(current_user.id)
    
    try:
        deleted_count = chat_service.clear_all_chats(user_id_str)
        return {"message": f"Successfully cleared {deleted_count} chat conversations"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing all chat conversations: {str(e)}"
        )

@api_router.get("/system/status")
def get_system_status(current_user: User = Depends(get_current_user)):
    """Get system status and document processing information"""
    chat_service = ChatService()
    status_info = chat_service.get_system_status()
    return status_info

@api_router.get("/user/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user