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

  // Load chat history on mount
  useEffect(() => {
    if (user) {
      loadChatHistory();
    }
  }, [user]);

  const loadChatHistory = async () => {
    try {
      const response = await chatAPI.getHistory();
      const history = Array.isArray(response.data) ? response.data : [];
      const sortedHistory = history.sort(
        (a, b) =>
          new Date(b.updated_at || b.createdAt || b.timestamp) -
          new Date(a.updated_at || a.createdAt || a.timestamp)
      );
      setChatHistory(sortedHistory);
    } catch (error) {
      console.error('Error loading chat history:', error);
      setChatHistory([]);
    }
  };

  // Update messages when switching chats
  useEffect(() => {
    if (currentChat) {
      if (currentChat.messages && currentChat.messages.length > 0) {
        const formatted = currentChat.messages.map((msg, index) => ({
          id: `${index}-${msg.timestamp}`,
          content: msg.content || msg.query || '',
          timestamp: msg.timestamp,
          isUser: msg.role === 'user',
          source: msg.source_document,
          confidence: msg.confidence
        }));
        setMessages(formatted);
      }
      setIsNewChat(false);
    } else {
      setMessages([]);
      setIsNewChat(true);
    }
  }, [currentChat]);

  /**
   * Handles when a new message (user + assistant) arrives
   * This function receives `newMessage` and `chatIdFromResponse` from ChatWindow
   */
  const handleNewMessage = async (newMessage, chatIdFromResponse) => {
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

    // Existing chat → append messages
    if (currentChat && !isNewChat) {
      const updatedMessages = [...messages, userMessage, assistantMessage];

      const updatedChat = {
        ...currentChat,
        _id: currentChat._id || chatIdFromResponse, // 👈 store backend chat_id if new
        messages: updatedMessages,
        updatedAt: new Date().toISOString(),
        lastMessage: newMessage.query,
        lastResponse: newMessage.response
      };

      const updatedHistory = chatHistory.map((chat) =>
        chat._id === currentChat._id ? updatedChat : chat
      );

      setChatHistory(updatedHistory);
      setCurrentChat(updatedChat);
      setMessages(updatedMessages);
    } else {
      // New chat → first message
      const newChat = {
        _id: chatIdFromResponse || null, // 👈 backend chat_id returned
        title: newMessage.query.slice(0, 40),
        query: newMessage.query,
        response: newMessage.response,
        lastMessage: newMessage.query,
        timestamp: newMessage.timestamp,
        source_document: newMessage.source_document,
        confidence: newMessage.confidence,
        messages: [userMessage, assistantMessage]
      };

      setChatHistory([newChat, ...chatHistory]);
      setCurrentChat(newChat);
      setIsNewChat(false);
      setMessages([userMessage, assistantMessage]);
    }
  };

  // Handle selecting chat from sidebar
  const handleSelectChat = (chat) => {
    setCurrentChat(chat);
    setIsNewChat(false);
  };

  // Delete individual chat
  const handleDeleteChat = async (chatToDelete) => {
    try {
      if (chatToDelete._id) {
        await chatAPI.deleteChat(chatToDelete._id);
      }
      await loadChatHistory();
      if (currentChat && currentChat._id === chatToDelete._id) {
        setCurrentChat(null);
        setIsNewChat(true);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
      await loadChatHistory();
    }
  };

  // Clear all chats
  const handleClearAll = async () => {
    try {
      await chatAPI.clearAllChats();
      setChatHistory([]);
      setCurrentChat(null);
      setMessages([]);
      setIsNewChat(true);
    } catch (error) {
      console.error('Error clearing chats:', error);
      setChatHistory([]);
      setCurrentChat(null);
      setMessages([]);
      setIsNewChat(true);
    }
  };

  // Start a fresh chat
  const handleNewChat = () => {
    setCurrentChat(null);
    setIsNewChat(true);
    setMessages([]);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Sidebar */}
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

      {/* Chat Window */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          sidebarOpen ? 'ml-80' : 'ml-0'
        }`}
      >
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
