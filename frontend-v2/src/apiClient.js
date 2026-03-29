// Simple helper to build API URLs that work in local dev and production (Render)
// Uses VITE_API_BASE_URL if defined, otherwise falls back to relative paths.

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

export function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const csrfToken = getCookie('csrf_token');
  const mergedOptions = {
    credentials: 'include',
    ...options,
    headers: {
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      ...(options.headers || {}),
    },
  };
  return fetch(url, mergedOptions);
}

export function getApiBase() {
  return API_BASE;
}
