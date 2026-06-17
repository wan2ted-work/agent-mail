import axios from 'axios';
import { API_URL } from '../config';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Normalize errors so callers can just read `err.message` — it carries the
// backend's `{ error }` text when present, otherwise the transport error.
api.interceptors.response.use(
  (response) => response,
  (err) => {
    const serverMsg = err.response?.data?.error || err.response?.data?.detail;
    return Promise.reject(new Error(serverMsg || err.message));
  }
);

// Instance API
export const instanceApi = {
  // Get instance by secret (UUID) — creates automatically if it doesn't exist.
  get(secret) {
    return api.get(`/instances/${secret}`);
  },

  // Update instance
  update(secret, data) {
    return api.put(`/instances/${secret}`, data);
  },

  // Delete instance
  delete(secret) {
    return api.delete(`/instances/${secret}`);
  },

  // Get all keys for instance
  getKeys(secret) {
    return api.get(`/instances/${secret}/keys`);
  },

  // Add new key to instance
  addKey(secret, key) {
    return api.post(`/instances/${secret}/keys`, { key });
  },

  // Remove key from instance
  removeKey(secret, key) {
    return api.delete(`/instances/${secret}/keys/${key}`);
  },

  // Custom domains
  getDomains(secret) {
    return api.get(`/instances/${secret}/domains`);
  },

  addDomain(secret, domain) {
    return api.post(`/instances/${secret}/domains`, { domain });
  },

  verifyDomain(secret, domain) {
    return api.post(`/instances/${secret}/domains/${domain}/verify`);
  },

  removeDomain(secret, domain) {
    return api.delete(`/instances/${secret}/domains/${domain}`);
  },
};

// Email API
export const emailApi = {
  // Get emails for instance
  getList(secret, params = {}) {
    return api.get(`/instances/${secret}/emails`, { params });
  },

  // Get email detail
  getDetail(secret, emailId) {
    return api.get(`/instances/${secret}/emails/${emailId}`);
  },

  // Get orphaned emails
  getOrphaned(params = {}) {
    return api.get('/emails/orphaned', { params });
  },
};

export default api;
