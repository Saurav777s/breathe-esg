// src/api/client.js
import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
});

API.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

API.interceptors.response.use(
  res => res,
  async err => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        const res = await axios.post('/api/auth/token/refresh/', { refresh });
        localStorage.setItem('access_token', res.data.access);
        err.config.headers.Authorization = `Bearer ${res.data.access}`;
        return axios(err.config);
      }
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default API;