/* api.js — thin wrapper around the GeoLabeler REST API */
const API_BASE = window.__API_BASE__ || 'http://localhost:5000/api';

const Api = (() => {
  let _token = localStorage.getItem('gl_token') || '';

  function setToken(t) { _token = t; localStorage.setItem('gl_token', t); }
  function clearToken() { _token = ''; localStorage.removeItem('gl_token'); localStorage.removeItem('gl_user'); }
  function hasToken() { return !!_token; }

  async function request(method, path, body, isForm = false) {
    const headers = {};
    if (_token) headers['Authorization'] = `Bearer ${_token}`;
    if (!isForm) headers['Content-Type'] = 'application/json';

    const opts = { method, headers };
    if (body) opts.body = isForm ? body : JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);
    const json = await res.json().catch(() => ({}));

    if (res.status === 401) {
      clearToken();
      window.location.reload();
    }
    if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
    return json;
  }

  return {
    setToken, clearToken, hasToken,
    get:    (p)      => request('GET',    p),
    post:   (p, b)   => request('POST',   p, b),
    put:    (p, b)   => request('PUT',    p, b),
    delete: (p)      => request('DELETE', p),
    upload: (p, fd)  => request('POST',   p, fd, true),

    /* AUTH */
    login:    (data) => request('POST', '/auth/login',    data),
    register: (data) => request('POST', '/auth/register', data),
    logout:   ()     => request('DELETE', '/auth/logout'),
    me:       ()     => request('GET',  '/auth/me'),

    /* DATASETS */
    getDatasets: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request('GET', `/datasets/?${q}`);
    },
    getDataset:    (id)   => request('GET',    `/datasets/${id}`),
    createDataset: (data) => request('POST',   `/datasets/`, data),
    updateDataset: (id, data) => request('PUT', `/datasets/${id}`, data),
    deleteDataset: (id)   => request('DELETE', `/datasets/${id}`),
    exportDataset: (id, fmt) => request('GET', `/datasets/${id}/export?format=${fmt}`),
    datasetStats:  (id)   => request('GET',    `/datasets/${id}/stats`),

    /* IMAGES */
    getImages: (datasetId, params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request('GET', `/images/dataset/${datasetId}?${q}`);
    },
    getImage:    (id) => request('GET',    `/images/${id}?include_annotations=true`),
    deleteImage: (id) => request('DELETE', `/images/${id}`),
    lockImage:   (id) => request('POST',   `/images/${id}/lock`),
    unlockImage: (id) => request('POST',   `/images/${id}/unlock`),
    aiSuggest:   (id) => request('POST',   `/images/${id}/ai-suggest`),
    uploadImages: (datasetId, formData) =>
      request('POST', `/images/dataset/${datasetId}/upload`, formData, true),
    imageFileUrl: (id) => `${API_BASE}/images/${id}/file`,
    thumbnailUrl: (id) => `${API_BASE}/images/${id}/thumbnail`,

    /* ANNOTATIONS */
    getAnnotations: (imageId, params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request('GET', `/annotations/image/${imageId}?${q}`);
    },
    createAnnotation: (imageId, data) => request('POST', `/annotations/image/${imageId}`, data),
    bulkCreateAnnotations: (imageId, data) => request('POST', `/annotations/image/${imageId}/bulk`, data),
    updateAnnotation: (id, data) => request('PUT', `/annotations/${id}`, data),
    deleteAnnotation: (id)       => request('DELETE', `/annotations/${id}`),
    reviewAnnotation: (id, data) => request('POST', `/annotations/${id}/review`, data),
  };
})();

window.Api = Api;
