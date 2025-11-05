// services/api.js
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const chatAPI = {
  sendMessage: (message, chatId = null) =>api.post('/chat/query', { message, chat_id: chatId }),

  getHistory: () => api.get('/chat/history'),
  deleteChat: (chatId) => api.delete(`/chat/${chatId}`),
  clearAllChats: () => api.delete('/chat/history'),
};

export const authAPI = {
  login: (username, password) => api.post(`/login?username=${username}&password=${password}`),
  register: (userData) => api.post('/register', userData),
};

export const userAPI = {
  getCurrentUser: () => api.get('/user/me'),
};

export default api;