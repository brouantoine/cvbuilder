/**
 * Client API : base URL + en-tête Authorization JWT
 */
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const AUTH_UNAUTHORIZED_EVENT = "auth:unauthorized";

function getToken() {
  return localStorage.getItem("access") || "";
}

function clearStoredAuth() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("auth");
}

function isAuthEndpoint(endpoint) {
  return (
    endpoint.startsWith("/api/auth/login/") ||
    endpoint.startsWith("/api/auth/register/") ||
    endpoint.startsWith("/api/auth/refresh/")
  );
}

function notifyUnauthorized(endpoint) {
  clearStoredAuth();
  if (!isAuthEndpoint(endpoint)) {
    window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
  }
}

// Rafraîchissement du token d'accès via le refresh token (verrou partagé pour
// éviter plusieurs rafraîchissements simultanés). Renvoie true si réussi.
let refreshPromise = null;
function refreshAccessToken() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return Promise.resolve(false);
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const data = await res.json().catch(() => ({}));
        if (data.access) {
          localStorage.setItem("access", data.access);
          if (data.refresh) localStorage.setItem("refresh", data.refresh);
          return true;
        }
        return false;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

// fetch authentifié : sur 401, tente un rafraîchissement puis rejoue 1 fois.
async function authedFetch(url, fetchOptions, baseHeaders, auth, endpoint) {
  const withToken = () => {
    const token = getToken();
    return auth && token ? { ...baseHeaders, Authorization: `Bearer ${token}` } : baseHeaders;
  };
  let res = await fetch(url, { ...fetchOptions, headers: withToken() });
  if (res.status === 401 && auth && !isAuthEndpoint(endpoint)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await fetch(url, { ...fetchOptions, headers: withToken() });
    }
  }
  return res;
}

export async function api(endpoint, options = {}) {
  const { auth = true, headers: optionHeaders = {}, ...fetchOptions } = options;
  const url = endpoint.startsWith("http") ? endpoint : `${BASE}${endpoint}`;
  const isFormData = fetchOptions.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...optionHeaders,
  };

  const res = await authedFetch(url, fetchOptions, headers, auth, endpoint);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) notifyUnauthorized(endpoint);
    throw { status: res.status, ...data };
  }
  return data;
}

function filenameFromDisposition(disposition) {
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ""));
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return filenameMatch?.[1] || "";
}

export async function apiBlob(endpoint, options = {}) {
  const { auth = true, headers: optionHeaders = {}, ...fetchOptions } = options;
  const url = endpoint.startsWith("http") ? endpoint : `${BASE}${endpoint}`;
  const headers = { ...optionHeaders };

  const res = await authedFetch(url, fetchOptions, headers, auth, endpoint);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) notifyUnauthorized(endpoint);
    throw { status: res.status, ...data };
  }

  return {
    blob: await res.blob(),
    filename: filenameFromDisposition(res.headers.get("content-disposition") || ""),
  };
}

// Auth
export const authApi = {
  register: (body) => api("/api/auth/register/", { auth: false, method: "POST", body: JSON.stringify(body) }),
  login: (body) => api("/api/auth/login/", { auth: false, method: "POST", body: JSON.stringify(body) }),
  me: () => api("/api/auth/me/"),
};

// Templates
export const templatesApi = {
  list: () => api("/api/templates/", { auth: false }),
  get: (id) => api(`/api/templates/${id}/`, { auth: false }),
  syncLibrary: () => api("/api/templates/sync-library/", { method: "POST" }),
};

// CVs
export const cvsApi = {
  list: () => api("/api/cvs/"),
  get: (id) => api(`/api/cvs/${id}/`),
  create: (body) => api("/api/cvs/", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => api(`/api/cvs/${id}/`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (id) => api(`/api/cvs/${id}/`, { method: "DELETE" }),
  uploadContext: (id, body) => api(`/api/cvs/${id}/context/`, { method: "POST", body }),
  improve: (id, body = {}) => api(`/api/cvs/${id}/ai/improve/`, { method: "POST", body: JSON.stringify(body) }),
  generate: (id) => api(`/api/cvs/${id}/generate/`, { method: "POST" }),
  preview: (body) => api("/api/cvs/preview/", { method: "POST", body: JSON.stringify(body) }),
  rewrite: (body) => api("/api/cvs/rewrite/", { method: "POST", body: JSON.stringify(body) }),
  writeProfile: (body) => api("/api/cvs/profile/", { method: "POST", body: JSON.stringify(body) }),
  correct: (body) => api("/api/cvs/correct/", { method: "POST", body: JSON.stringify(body) }),
  duplicate: (id) => api(`/api/cvs/${id}/duplicate/`, { method: "POST" }),
  download: (id, format = "pdf") => apiBlob(`/api/cvs/${id}/download/?file=${format}`),
  plans: (cvId) => api(`/api/cvs/plans/${cvId ? `?cv=${cvId}` : ""}`),
};

export const paymentsApi = {
  initialize: (body) => api("/api/cvs/payments/initialize/", { method: "POST", body: JSON.stringify(body) }),
  verify: (body) => api("/api/cvs/payments/verify/", { method: "POST", body: JSON.stringify(body) }),
};
