import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import { chatAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const Chat = () => {
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState([]);
  const [isNewChat, setIsNewChat] = useState(true);
  const { user } = useAuth();

  // Load chat history from backend API
  useEffect(() => {
    if (user) {
      loadChatHistory();
    }
  }, [user]);

  const loadChatHistory = async () => {
    try {
      console.log('Loading chat history for user:', user?.username);
      const response = await chatAPI.getHistory();
      console.log('Backend chat history response:', response.data);
      
      // Ensure we have an array and sort by timestamp
      const history = Array.isArray(response.data) ? response.data : [];
      const sortedHistory = history.sort((a, b) => 
        new Date(b.timestamp || b.createdAt) - new Date(a.timestamp || a.createdAt)
      );
      
      setChatHistory(sortedHistory);
    } catch (error) {
      console.error('Error loading chat history from backend:', error);
      setChatHistory([]);
    }
  };

  // Transform current chat to messages when it changes
  useEffect(() => {
    if (currentChat) {
      if (currentChat.messages && currentChat.messages.length > 0) {
        setMessages(currentChat.messages);
      } else {
        const convertedMessages = [
          { 
            id: `${currentChat.timestamp}-query`, 
            content: currentChat.query, 
            timestamp: currentChat.timestamp, 
            isUser: true 
          },
          { 
            id: `${currentChat.timestamp}-response`, 
            content: currentChat.response, 
            timestamp: currentChat.timestamp, 
            isUser: false,
            source: currentChat.source_document,
            confidence: currentChat.confidence
          }
        ];
        setMessages(convertedMessages);
      }
      setIsNewChat(false);
    } else if (isNewChat) {
      setMessages([]);
    }
  }, [currentChat, isNewChat]);

  const handleNewMessage = async (newMessage) => {
    const userMessage = {
      id: `${Date.now()}-user`,
      content: newMessage.query,
      timestamp: newMessage.timestamp,
      isUser: true
    };

    const assistantMessage = {
      id: `${Date.now()}-assistant`,
      content: newMessage.response,
      timestamp: newMessage.timestamp,
      isUser: false,
      source: newMessage.source_document,
      confidence: newMessage.confidence
    };

    if (currentChat && !isNewChat) {
      // Update existing chat
      const updatedMessages = [
        ...messages,
        userMessage,
        assistantMessage
      ];

      const updatedChat = {
        ...currentChat,
        messages: updatedMessages,
        lastMessage: newMessage.query,
        lastResponse: newMessage.response,
        timestamp: newMessage.timestamp,
        updatedAt: new Date().toISOString(),
        query: currentChat.query || newMessage.query,
        response: currentChat.response || newMessage.response,
        source_document: newMessage.source_document,
        confidence: newMessage.confidence
      };

      const updatedHistory = chatHistory.map(chat => 
        chat._id === currentChat._id ? updatedChat : chat
      );
      
      setChatHistory(updatedHistory);
      setCurrentChat(updatedChat);
      setMessages(updatedMessages);
      
    } else {
      // Create new chat
      const newChat = {
        query: newMessage.query,
        response: newMessage.response,
        lastMessage: newMessage.query,
        timestamp: newMessage.timestamp,
        source_document: newMessage.source_document,
        confidence: newMessage.confidence,
        messages: [userMessage, assistantMessage],
      };

      // Add to history and refresh from backend to get the actual saved chat
      const updatedHistory = [newChat, ...chatHistory];
      setChatHistory(updatedHistory);
      setCurrentChat(newChat);
      setIsNewChat(false);
      setMessages([userMessage, assistantMessage]);
      
      // Reload history to get the properly saved chat from backend
      setTimeout(() => {
        loadChatHistory();
      }, 500);
    }
  };

  const handleSelectChat = (chat) => {
    setCurrentChat(chat);
    setIsNewChat(false);
  };

  const handleDeleteChat = async (chatToDelete) => {
    try {
      if (chatToDelete._id) {
        await chatAPI.deleteChat(chatToDelete._id);
      }
      
      // Reload history from backend after deletion
      await loadChatHistory();
      
      if (currentChat && currentChat._id === chatToDelete._id) {
        setCurrentChat(null);
        setIsNewChat(true);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
      // Even if API call fails, update UI and reload history
      await loadChatHistory();
    }
  };

  const handleClearAll = async () => {
    try {
      await chatAPI.clearAllChats();
      setChatHistory([]);
      setCurrentChat(null);
      setMessages([]);
      setIsNewChat(true);
    } catch (error) {
      console.error('Error clearing all chats:', error);
      // Update UI even if API call fails
      setChatHistory([]);
      setCurrentChat(null);
      setMessages([]);
      setIsNewChat(true);
    }
  };

  const handleNewChat = () => {
    setCurrentChat(null);
    setIsNewChat(true);
    setMessages([]);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <Sidebar
        chatHistory={chatHistory}
        onSelectChat={handleSelectChat}
        currentChat={currentChat}
        onDeleteChat={handleDeleteChat}
        onClearAll={handleClearAll}
        onNewChat={handleNewChat}
        isNewChat={isNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        sidebarOpen ? 'ml-80' : 'ml-0'
      }`}>
        <ChatWindow
          messages={messages}
          onNewMessage={handleNewMessage}
          currentChat={currentChat}
          isNewChat={isNewChat}
          onClearAll={handleClearAll}
        />
      </div>
    </div>
  );
};

export default Chat;