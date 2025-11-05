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
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const { user } = useAuth();

  const cleanMessages = (msgs = []) => {
  return msgs
    .filter(msg => msg && msg.content && msg.role) // remove invalid
    .map(msg => ({
      ...msg,
      isTemp: false,
      id: msg.id?.replace(/^temp-/, '') || `${Date.now()}-${msg.role}`,
      content: msg.content.replace('(sending...)', '').trim(),
    }));
};


  // Load chat history
  useEffect(() => {
    if (user) loadChatHistory();
  }, [user]);

  const loadChatHistory = async () => {
  setIsLoadingHistory(true);
  try {
    const response = await chatAPI.getHistory();
    const history = Array.isArray(response.data) ? response.data : [];
    const sortedHistory = history.sort(
      (a, b) =>
        new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
    );

    // Clean all chats before saving
    const cleanedHistory = sortedHistory.map(chat => ({
      ...chat,
      messages: cleanMessages(chat.messages)
    }));

    setChatHistory(cleanedHistory);

    if (currentChat) {
      const updated = cleanedHistory.find(c => c._id === currentChat._id);
      if (updated) setCurrentChat(updated);
    }
  } catch (error) {
    console.error('Error loading chat history:', error);
    setChatHistory([]);
  } finally {
    setIsLoadingHistory(false);
  }
};

  // Update message display when chat changes - WITH DEBOUNCING
  useEffect(() => {
  if (currentChat && currentChat.messages) {
    setMessages(cleanMessages(currentChat.messages));
    setIsNewChat(false);
  } else {
    setMessages([]);
  }
}, [currentChat]);


  // Handle sending new messages - FIXED VERSION
  const handleNewMessage = async (newMessage, chatId = null) => {
    const newMsgs = newMessage.messages || [];
    
    if (newMsgs.length === 0) return;

    const timestamp = new Date().toISOString();

    // Filter out any temporary markers
    const cleanNewMessages = newMsgs.map(msg => ({
      ...msg,
      content: msg.content.replace('(sending...)', '').trim()
    })).filter(msg => msg.content.length > 0);

    if (cleanNewMessages.length === 0) return;

    if (currentChat && !isNewChat) {
      // For existing chat - merge avoiding duplicates
      const existingMessageIds = new Set(messages.map(msg => msg.id));
      const uniqueNewMessages = cleanNewMessages.filter(msg => !existingMessageIds.has(msg.id));
      
      if (uniqueNewMessages.length === 0) return;

      const updatedMessages = [...messages, ...uniqueNewMessages];
      const updatedChat = {
        ...currentChat,
        messages: updatedMessages,
        updated_at: timestamp,
      };
      
      setCurrentChat(updatedChat);
      setMessages(updatedMessages);

      // Update chat history locally
      setChatHistory(prev => 
        prev.map(chat => 
          chat._id === currentChat._id ? updatedChat : chat
        )
      );
    } else {
      // Create new chat
      const newChatId = chatId || newMessage.chat_id || `chat-${Date.now()}`;
      const newChat = {
        _id: newChatId,
        messages: cleanNewMessages,
        created_at: timestamp,
        updated_at: timestamp,
        title: cleanNewMessages[0]?.content?.substring(0, 30) + (cleanNewMessages[0]?.content?.length > 30 ? '...' : '') || 'New Chat',
      };
      
      setChatHistory(prev => [newChat, ...prev]);
      setCurrentChat(newChat);
      setMessages(cleanNewMessages);
      setIsNewChat(false);
    }

    
  };

  // Select existing chat - FIXED
  const handleSelectChat = (chat) => {
    if (isLoadingHistory) return; // Don't allow selection while loading
    
    // Ensure chat messages are clean
    const cleanChat = {
      ...chat,
      messages: (chat.messages || []).filter(msg => 
        msg.content && !msg.content.includes('(sending...)')
      )
    };
    
    setCurrentChat(cleanChat);
    setIsNewChat(false);
  };

  // Delete a single chat
  const handleDeleteChat = async (chatToDelete) => {
    try {
      if (chatToDelete._id) await chatAPI.deleteChat(chatToDelete._id);
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
      console.error('Error clearing all chats:', error);
      setChatHistory([]);
    }
  };

  const handleNewChat = () => {
    setCurrentChat(null);
    setMessages([]);
    setIsNewChat(true);
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
        isLoading={isLoadingHistory}
      />

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
          isLoadingHistory={isLoadingHistory}
        />
      </div>
    </div>
  );
};

export default Chat;