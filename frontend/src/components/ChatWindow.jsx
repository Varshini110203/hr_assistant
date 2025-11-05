import React, { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';

const ChatWindow = ({ messages, onNewMessage, currentChat, isNewChat, onClearAll }) => {
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const timestamp = new Date().toISOString();

    const userMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: inputMessage,
      timestamp,
    };

    setInputMessage('');
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(inputMessage, currentChat?._id);

      const assistantMessage = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: response.data.response,
        timestamp,
        source: response.data.source_document,
        confidence: response.data.confidence,
      };

      if (onNewMessage) {
        onNewMessage(
          {
            query: inputMessage,
            response: response.data.response,
            timestamp,
            source_document: response.data.source_document,
            confidence: response.data.confidence,
            messages: [userMessage, assistantMessage],
          },
          response.data.chat_id
        );
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: `${Date.now()}-error`,
        role: 'assistant',
        content: '⚠️ Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      if (onNewMessage) {
        onNewMessage({
          messages: [userMessage, errorMessage],
        });
      }
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const suggestedQuestions = [
    'What is the leave policy?',
    'How do I apply for sick leave?',
    'What are the working hours?',
    'Tell me about employee benefits',
  ];

  const handleSuggestionClick = (question) => {
    setInputMessage(question);
    inputRef.current?.focus();
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                {isNewChat ? 'Start New Conversation' : 'Chat History'}
              </h1>
              {currentChat && (
                <p className="text-sm text-gray-500 mt-0.5">
                  {currentChat.query?.substring(0, 60)}
                  {currentChat.query?.length > 60 ? '...' : ''}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-6">
          {messages.length === 0 && isNewChat ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center w-full max-w-2xl">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                  <svg
                    className="w-8 h-8 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Welcome to HR Assistant</h3>
                <p className="text-gray-600 mb-8 text-base">
                  I'm here to help you with HR policies, leave management, and company guidelines.
                </p>
                <div className="space-y-3 mt-8 mb-12">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(question)}
                      className="w-full p-4 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg text-left transition-all duration-200 group hover:border-gray-300"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0 w-5 h-5 border-2 border-gray-300 rounded group-hover:border-blue-500 transition-colors flex items-center justify-center">
                          <div className="w-2 h-2 bg-blue-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        </div>
                        <span className="text-sm text-gray-700 group-hover:text-gray-900">
                          {question}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => {
                const role = message.role || (message.isUser ? 'user' : 'assistant');
                return (
                  <div
                    key={message.id || index}
                    className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`flex items-start space-x-3 max-w-4xl ${
                        role === 'user'
                          ? 'flex-row-reverse space-x-reverse'
                          : 'flex-row'
                      }`}
                    >
                      {/* Avatar */}
                      <div
                        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                          role === 'user' ? 'bg-blue-600' : 'bg-purple-600'
                        }`}
                      >
                        {role === 'user' ? (
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                            />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                            />
                          </svg>
                        )}
                      </div>

                      {/* Message bubble */}
                      <div className={`flex flex-col ${role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div
                          className={`rounded-lg px-4 py-3 ${
                            role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          <div className="whitespace-pre-wrap text-sm leading-relaxed">
                            {message.content}
                          </div>
                        </div>

                        {/* Timestamp */}
                        <div
                          className={`text-xs text-gray-400 mt-1 px-1 ${
                            role === 'user' ? 'text-right' : 'text-left'
                          }`}
                        >
                          {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <form onSubmit={sendMessage} className="flex items-end space-x-3">
            <div className="flex-1 bg-white border border-gray-300 rounded-lg focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all duration-200">
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(e);
                  }
                }}
                placeholder="Type your message here... (Shift+Enter for new line)"
                className="w-full bg-transparent px-4 py-3 focus:outline-none resize-none text-gray-800 placeholder-gray-500 text-sm"
                rows="1"
                style={{ minHeight: '48px', maxHeight: '120px' }}
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
