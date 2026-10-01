/**
 * DAIC Archive - Unified API Client
 * Interfaces with FastAPI backend with structured error handling.
 */

const API_BASE = '/api';

const api = {
  async health() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return await res.json();
    } catch (e) {
      console.warn("API health check failed, running with offline state:", e);
      return { status: "offline", data_mode: "demo", is_demo_mode: true };
    }
  },

  async ask(question, language = 'en') {
    const res = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, language })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Archival retrieval error" }));
      throw new Error(err.detail || "Unable to complete archival query.");
    }
    return await res.json();
  },

  async retrieve(query, top_k = 15) {
    const res = await fetch(`${API_BASE}/retrieve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k })
    });
    if (!res.ok) throw new Error("Failed to retrieve candidate evidence.");
    return await res.json();
  },

  async verify(chunk_id) {
    const res = await fetch(`${API_BASE}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: "", chunk_id })
    });
    return await res.json();
  },

  async getArchive(params = {}) {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.type && params.type !== 'All') query.set('type', params.type);
    if (params.year) query.set('year', params.year);
    if (params.collection && params.collection !== 'All') query.set('collection', params.collection);
    if (params.language && params.language !== 'All') query.set('language', params.language);
    if (params.verification_status && params.verification_status !== 'All') query.set('verification_status', params.verification_status);
    if (params.provenance_type && params.provenance_type !== 'All') query.set('provenance_type', params.provenance_type);

    const res = await fetch(`${API_BASE}/archive?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch archival documents.");
    return await res.json();
  },

  async getDocument(id) {
    const res = await fetch(`${API_BASE}/archive/${id}`);
    if (!res.ok) throw new Error("Document not found in archival repository.");
    return await res.json();
  },

  async getTimeline(category = null) {
    const url = category && category !== 'All' 
      ? `${API_BASE}/timeline?category=${encodeURIComponent(category)}`
      : `${API_BASE}/timeline`;
    const res = await fetch(url);
    return await res.json();
  },

  async getKnowledge() {
    const res = await fetch(`${API_BASE}/knowledge`);
    return await res.json();
  },

  async getMedia(type = null) {
    const url = type && type !== 'All' ? `${API_BASE}/media?media_type=${encodeURIComponent(type)}` : `${API_BASE}/media`;
    const res = await fetch(url);
    return await res.json();
  },

  async getStories() {
    const res = await fetch(`${API_BASE}/stories`);
    return await res.json();
  },

  async getStory(slug) {
    const res = await fetch(`${API_BASE}/stories/${slug}`);
    return await res.json();
  },

  async getResearch() {
    const res = await fetch(`${API_BASE}/research`);
    return await res.json();
  },

  async saveResearch(item) {
    const res = await fetch(`${API_BASE}/research/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    });
    return await res.json();
  },

  async deleteResearch(id) {
    const res = await fetch(`${API_BASE}/research/${id}`, { method: 'DELETE' });
    return await res.json();
  },

  async getAdminStats() {
    const res = await fetch(`${API_BASE}/admin/stats`);
    return await res.json();
  },

  async uploadDocument(formData) {
    const res = await fetch(`${API_BASE}/admin/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload error");
    }
    return await res.json();
  },

  async uploadBatch(formData) {
    const res = await fetch(`${API_BASE}/admin/upload-batch`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Batch upload failed" }));
      throw new Error(err.detail || "Batch upload error");
    }
    return await res.json();
  },

  async getIngestJobs(limit = 50) {
    const res = await fetch(`${API_BASE}/admin/ingest-jobs?limit=${limit}`);
    if (!res.ok) return { total: 0, jobs: [] };
    return await res.json();
  },

  async getAdminDocuments(limit = 100) {
    const res = await fetch(`${API_BASE}/admin/documents?limit=${limit}`);
    if (!res.ok) return { total: 0, documents: [] };
    return await res.json();
  },

  async getPendingOCR(docId = null) {
    const url = docId ? `${API_BASE}/admin/ocr-pending?doc_id=${encodeURIComponent(docId)}` : `${API_BASE}/admin/ocr-pending`;
    const res = await fetch(url);
    return await res.json();
  },

  async reviewOCR(ocrData) {
    const res = await fetch(`${API_BASE}/admin/ocr-review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ocrData)
    });
    return await res.json();
  },

  async getOCRRevisions(docId = null, ocrId = null) {
    let url = `${API_BASE}/admin/ocr-revisions`;
    if (ocrId) url += `?ocr_id=${encodeURIComponent(ocrId)}`;
    else if (docId) url += `?document_id=${encodeURIComponent(docId)}`;
    const res = await fetch(url);
    if (!res.ok) return { count: 0, revisions: [] };
    return await res.json();
  },

  async getIndexConsistency() {
    const res = await fetch(`${API_BASE}/admin/index-consistency`);
    if (!res.ok) return { is_healthy: false, status: "ERROR" };
    return await res.json();
  }
};

