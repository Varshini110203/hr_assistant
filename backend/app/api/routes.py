from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import UserCreate, User, Token
from app.models.chat import QueryRequest, QueryResponse
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.core.security import create_access_token
from app.api.dependencies import get_current_user
from datetime import timedelta
from app.core.config import settings
from bson import ObjectId

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
def login(username: str, password: str):
    auth_service = AuthService()
    user = auth_service.authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/chat/query", response_model=QueryResponse)
def chat_query(request: QueryRequest, current_user: User = Depends(get_current_user)):
    chat_service = ChatService()
    response = chat_service.process_query(current_user.id, request.message)
    return response

@api_router.get("/chat/history")
def get_chat_history(current_user: User = Depends(get_current_user)):
    chat_service = ChatService()
    history = chat_service.get_chat_history(current_user.id)
    return history

@api_router.delete("/chat/history/{message_id}")
def delete_chat_message(message_id: str, current_user: User = Depends(get_current_user)):
    """Delete a specific chat message by ID"""
    chat_service = ChatService()
    try:
        success = chat_service.delete_message(current_user.id, message_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        return {"message": "Chat message deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting message: {str(e)}"
        )

@api_router.delete("/chat/history")
def clear_all_chat_history(current_user: User = Depends(get_current_user)):
    """Clear all chat history for the current user"""
    chat_service = ChatService()
    try:
        success = chat_service.clear_user_history(current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear chat history"
            )
        return {"message": "All chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing chat history: {str(e)}"
        )

@api_router.get("/user/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user