import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import { chatAPI } from '../services/api';

const Chat = () => {
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    loadChatHistory();
  }, []);

  useEffect(() => {
    // When currentChat changes, update messages to display it
    if (currentChat) {
      setMessages([
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
      ]);
    } else {
      // If no current chat selected, show all history as messages
      transformChatHistoryToMessages();
    }
  }, [currentChat, chatHistory]);

  const loadChatHistory = async () => {
    try {
      const response = await chatAPI.getHistory();
      setChatHistory(response.data);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const transformChatHistoryToMessages = () => {
    const transformedMessages = chatHistory.flatMap(chat => [
      { 
        id: `${chat.timestamp}-query`, 
        content: chat.query, 
        timestamp: chat.timestamp, 
        isUser: true 
      },
      { 
        id: `${chat.timestamp}-response`, 
        content: chat.response, 
        timestamp: chat.timestamp, 
        isUser: false,
        source: chat.source_document,
        confidence: chat.confidence
      }
    ]);
    setMessages(transformedMessages);
  };

  const handleNewMessage = (newMessage) => {
    const updatedHistory = [newMessage, ...chatHistory];
    setChatHistory(updatedHistory);
    
    // Add the new message to the current messages view
    const newMessages = [
      { 
        id: `${newMessage.timestamp}-query`, 
        content: newMessage.query, 
        timestamp: newMessage.timestamp, 
        isUser: true 
      },
      { 
        id: `${newMessage.timestamp}-response`, 
        content: newMessage.response, 
        timestamp: newMessage.timestamp, 
        isUser: false,
        source: newMessage.source_document,
        confidence: newMessage.confidence
      }
    ];
    
    setMessages(prev => [...prev, ...newMessages]);
  };

  const handleSelectChat = (chat) => {
    setCurrentChat(chat);
  };

  const handleDeleteChat = async (chatToDelete) => {
    try {
      await chatAPI.deleteChat(chatToDelete._id);
      const updatedHistory = chatHistory.filter(chat => chat._id !== chatToDelete._id);
      setChatHistory(updatedHistory);
      
      // If the deleted chat was the current one, clear it
      if (currentChat && currentChat._id === chatToDelete._id) {
        setCurrentChat(null);
      }
    } catch (error) {
      if (error.response?.status === 404) {
        // Message already deleted, remove from frontend
        const updatedHistory = chatHistory.filter(chat => chat._id !== chatToDelete._id);
        setChatHistory(updatedHistory);
      } else {
        console.error('Error deleting chat:', error);
      }
    }
  };

  const handleClearAll = async () => {
    try {
      await chatAPI.clearAllChats();
      setChatHistory([]);
      setCurrentChat(null);
      setMessages([]);
    } catch (error) {
      if (error.response?.status === 500) {
        // Still clear from frontend even if backend fails
        setChatHistory([]);
        setCurrentChat(null);
        setMessages([]);
      } else {
        console.error('Error clearing all chats:', error);
      }
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        chatHistory={chatHistory}
        onSelectChat={handleSelectChat}
        currentChat={currentChat}
        onDeleteChat={handleDeleteChat}
        onClearAll={handleClearAll}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      
      {/* Main content area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        sidebarOpen ? 'ml-64' : 'ml-0'
      }`}>
        <ChatWindow
          messages={messages}
          onNewMessage={handleNewMessage}
          currentChat={currentChat}
        />
      </div>
    </div>
  );
};

export default Chat;