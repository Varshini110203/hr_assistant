import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Sidebar = ({ 
  chatHistory, 
  onSelectChat, 
  currentChat, 
  onDeleteChat, 
  onClearAll,
  isOpen, 
  onToggle 
}) => {
  const { user, logout } = useAuth();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDeleteChat = (chat, e) => {
    e.stopPropagation();
    onDeleteChat(chat);
  };

  const handleClearAll = () => {
    setShowDeleteConfirm(true);
  };

  const confirmClearAll = () => {
    onClearAll();
    setShowDeleteConfirm(false);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-50 bg-primary-600 text-white p-2 rounded-lg shadow-lg hover:bg-primary-700"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    );
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full fixed left-0 top-0 z-40">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">HR Assistant</h1>
          <p className="text-sm text-gray-600 mt-1">Welcome, {user?.username}</p>
        </div>
        <button
          onClick={onToggle}
          className="text-gray-500 hover:text-gray-700 p-1 rounded"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Chat History Section */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            Chat History
          </h2>
          {chatHistory.length > 0 && (
            <button
              onClick={handleClearAll}
              className="text-xs text-red-600 hover:text-red-700 font-medium"
            >
              Clear All
            </button>
          )}
        </div>
        
        {showDeleteConfirm && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800 mb-2">Clear all chat history?</p>
            <div className="flex space-x-2">
              <button
                onClick={confirmClearAll}
                className="flex-1 bg-red-600 text-white py-1 px-2 rounded text-xs hover:bg-red-700"
              >
                Yes
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 bg-gray-300 text-gray-700 py-1 px-2 rounded text-xs hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        )}


<div className="space-y-1">
  {chatHistory.length === 0 ? (
    <p className="text-sm text-gray-500 text-center py-4">
      No chat history yet
    </p>
  ) : (
    chatHistory.map((chat, index) => (
      <div
        key={chat._id || index}
        className={`group relative p-2 rounded cursor-pointer ${
          currentChat?._id === chat._id 
            ? 'bg-primary-100 text-primary-700 border border-primary-300' 
            : 'text-gray-700 hover:bg-gray-100 border border-transparent'
        }`}
        onClick={() => onSelectChat(chat)}
      >
        <div className="pr-6">
          <div className="truncate text-sm font-medium mb-1">
            {chat.query.substring(0, 35)}
            {chat.query.length > 35 && '...'}
          </div>
          <div className="text-xs text-gray-500">
            {new Date(chat.timestamp).toLocaleDateString()} • {new Date(chat.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </div>
        </div>
        
        {/* Delete button for individual chat */}
        <button
          onClick={(e) => handleDeleteChat(chat, e)}
          className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 p-1 rounded transition-opacity"
          title="Delete this chat"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    ))
  )}
</div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={logout}
          className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded text-sm font-medium"
        >
          Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;