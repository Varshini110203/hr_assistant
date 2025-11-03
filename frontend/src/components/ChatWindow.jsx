import React, { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';

const ChatWindow = ({ messages, onNewMessage, currentChat }) => {
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userMessage = {
      id: Date.now().toString(),
      content: inputMessage,
      timestamp: new Date().toISOString(),
      isUser: true,
    };

    // Temporarily add user message to UI
    const tempMessages = [...messages, userMessage];
    // This would be handled by the parent component
    
    setInputMessage('');
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(inputMessage);
      const newMessage = {
        query: inputMessage,
        response: response.data.response,
        timestamp: new Date().toISOString(),
        source_document: response.data.source_document,
        confidence: response.data.confidence
      };

      if (onNewMessage) {
        onNewMessage(newMessage);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        query: inputMessage,
        response: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      };
      if (onNewMessage) {
        onNewMessage(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header showing current chat or general view */}
      <div className="border-b border-gray-200 bg-white p-4">
        <h1 className="text-xl font-semibold text-gray-800">
          {currentChat ? 'Chat History' : 'HR Assistant'}
        </h1>
        {currentChat && (
          <p className="text-sm text-gray-600 mt-1">
            Viewing: "{currentChat.query.substring(0, 50)}..."
          </p>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <h3 className="text-lg font-medium">Welcome to HR Assistant</h3>
            <p className="mt-2">Ask me anything about HR policies, leave, or company guidelines.</p>
            {currentChat && (
              <p className="mt-4 text-sm text-gray-400">
                Currently viewing a specific chat from your history
              </p>
            )}
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg px-4 py-2 ${
                  message.isUser
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {!message.isUser && message.source && (
                  <div className="text-xs mt-1 opacity-70">
                    Source: {message.source} 
                    {message.confidence && ` • Confidence: ${(message.confidence * 100).toFixed(1)}%`}
                  </div>
                )}
                <div className="text-xs mt-1 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </div>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 rounded-lg px-4 py-2">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={sendMessage} className="flex space-x-4">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your HR-related question..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatWindow;