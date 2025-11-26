// Simple helper to build API URLs that work in local dev and production (Render)
// Uses VITE_API_BASE_URL if defined, otherwise falls back to relative paths.

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  return fetch(url, options);
}

export function getApiBase() {
  return API_BASE;
}
