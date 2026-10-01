/**
 * AMBEDKAR DIGITAL LEGACY - Archivist Dashboard & Ingestion Controller
 * Phase II: Batch multi-file upload, enriched stats, document ingestion table.
 */

let pendingOCRRecords = [];
let currentSelectedOCR = null;

document.addEventListener('DOMContentLoaded', () => {
  initAdminDashboard();
});

function initAdminDashboard() {
  loadAdminStats();
  loadPendingOCR();
  loadDocumentTable();

  const form = document.getElementById('upload-form');
  if (form) {
    form.addEventListener('submit', handleDocumentUpload);
  }

  const select = document.getElementById('ocr-pending-select');
  if (select) {
    select.addEventListener('change', (e) => {
      const ocrId = e.target.value;
      selectOCRRecord(ocrId);
    });
  }

  const saveReviewedBtn = document.getElementById('save-ocr-reviewed-btn');
  if (saveReviewedBtn) {
    saveReviewedBtn.addEventListener('click', () => dispatchOCRReview('archivist_reviewed'));
  }

  const verifyPublishBtn = document.getElementById('verify-ocr-publish-btn');
  if (verifyPublishBtn) {
    verifyPublishBtn.addEventListener('click', () => dispatchOCRReview('verified'));
  }

  const rejectBtn = document.getElementById('reject-ocr-btn');
  if (rejectBtn) {
    rejectBtn.addEventListener('click', () => dispatchOCRReview('rejected'));
  }

  const returnBtn = document.getElementById('return-ocr-review-btn');
  if (returnBtn) {
    returnBtn.addEventListener('click', () => dispatchOCRReview('pending_review'));
  }

  const dupCancelBtn = document.getElementById('dup-cancel-btn');
  if (dupCancelBtn) {
    dupCancelBtn.addEventListener('click', () => {
      const alertBox = document.getElementById('duplicate-alert');
      if (alertBox) alertBox.classList.add('hidden');
    });
  }

  // Enable multi-file selection on the existing file input
  const fileInput = document.getElementById('upload-file');
  if (fileInput) {
    fileInput.setAttribute('multiple', 'multiple');
  }
}

async function loadAdminStats() {
  try {
    const stats = await api.getAdminStats();

    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '-'; };

    setEl('stat-total-docs', stats.total_documents);
    setEl('stat-real-docs', stats.real_archival_documents);
    setEl('stat-user-docs', stats.user_uploaded_documents);
    setEl('stat-demo-docs', stats.demo_documents);
    setEl('stat-verified-docs', stats.verified_documents);
    setEl('stat-pending-docs', stats.pending_review_documents);
    setEl('stat-chunks', stats.total_chunks);
    setEl('stat-fts', stats.fts_indexed_chunks);
    setEl('stat-faiss', stats.faiss_vectors);
    setEl('stat-ocr-pending', stats.ocr_pending_review);
    setEl('stat-ocr-reviewed', stats.ocr_reviewed);
    setEl('stat-duplicates', stats.duplicate_count);

    const modeBadge = document.getElementById('admin-mode-badge');
    if (modeBadge) modeBadge.textContent = `${stats.data_mode.toUpperCase()} MODE`;

    const auditList = document.getElementById('audit-log-list');
    if (auditList && stats.recent_logs) {
      if (stats.recent_logs.length === 0) {
        auditList.innerHTML = `<p class="text-gray-400 italic">No recent activity logged.</p>`;
      } else {
        auditList.innerHTML = stats.recent_logs.map(log => `
          <div class="p-2 rounded bg-gray-50 border border-gray-200">
            <div class="flex justify-between font-bold text-[#141F39]">
              <span>${log.action}</span>
              <span class="text-[10px] text-gray-400 font-normal">${new Date(log.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="text-gray-600 truncate mt-0.5">${log.details || ''}</div>
          </div>
        `).join('');
      }
    }

  } catch (e) {
    console.error("Failed to load admin stats:", e);
  }
}

async function loadPendingOCR(preferredId = null) {
  try {
    const data = await api.getPendingOCR();
    pendingOCRRecords = data.records || [];

    const select = document.getElementById('ocr-pending-select');
    if (!select) return;

    if (pendingOCRRecords.length === 0) {
      select.innerHTML = `<option value="">No pending OCR records found in queue</option>`;
      clearOCRDisplay();
      return;
    }

    select.innerHTML = pendingOCRRecords.map(r => {
      const statusIcon = r.archivist_status === 'verified' ? '✓' : (r.archivist_status === 'archivist_reviewed' ? '✎' : r.archivist_status === 'rejected' ? '✗' : '⏳');
      return `<option value="${r.id}">${statusIcon} [${r.document_id}] Page ${r.page}: ${r.doc_title || 'Untitled'}</option>`;
    }).join('');

    const targetId = preferredId || pendingOCRRecords[0].id;
    select.value = targetId;
    selectOCRRecord(targetId);

  } catch (err) {
    console.error("Failed to load pending OCR records:", err);
  }
}

async function selectOCRRecord(ocrId) {
  const record = pendingOCRRecords.find(r => r.id === ocrId);
  currentSelectedOCR = record || null;
  if (!record) return;

  const titleEl = document.getElementById('ocr-record-title');
  const confEl = document.getElementById('ocr-record-conf');
  const textEl = document.getElementById('ocr-review-text');
  const notesEl = document.getElementById('ocr-review-notes');
  const badgeEl = document.getElementById('ocr-station-badge');
  const imgBox = document.getElementById('ocr-facsimile-box');
  const imgEl = document.getElementById('ocr-facsimile-img');
  const updatedEl = document.getElementById('ocr-record-updated');
  const statusTextEl = document.getElementById('ocr-record-status-text');

  if (titleEl) titleEl.textContent = `${record.document_id} — Page ${record.page}`;

  if (confEl) {
    if (record.confidence !== null && record.confidence !== undefined) {
      confEl.textContent = `${(record.confidence * 100).toFixed(1)}% Confidence`;
      confEl.className = record.confidence >= 0.85 ? "text-green-700 font-mono text-[10px]" : "text-amber-700 font-mono text-[10px]";
    } else {
      confEl.textContent = "Confidence unavailable";
      confEl.className = "text-gray-500 font-mono text-[10px]";
    }
  }

  if (updatedEl) {
    updatedEl.textContent = record.updated_at ? new Date(record.updated_at).toLocaleString() : 'Recently';
  }

  if (statusTextEl) {
    statusTextEl.textContent = record.archivist_status || 'pending_review';
    statusTextEl.className = `font-bold uppercase text-[9px] px-1.5 py-0.5 rounded ${
      record.archivist_status === 'verified' ? 'bg-emerald-100 text-emerald-800' :
      record.archivist_status === 'rejected' ? 'bg-red-100 text-red-800' :
      record.archivist_status === 'archivist_reviewed' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
    }`;
  }

  if (textEl) textEl.value = record.recognized_text || '';
  if (notesEl) notesEl.value = record.notes || '';

  if (badgeEl) {
    if (record.archivist_status === 'verified') {
      badgeEl.textContent = "Verified Source";
      badgeEl.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800";
    } else if (record.archivist_status === 'archivist_reviewed') {
      badgeEl.textContent = "Archivist Reviewed";
      badgeEl.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800";
    } else if (record.archivist_status === 'rejected') {
      badgeEl.textContent = "Rejected";
      badgeEl.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800";
    } else {
      badgeEl.textContent = "Pending Review";
      badgeEl.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800";
    }
  }

  if (imgBox && imgEl) {
    if (record.image_path) {
      imgEl.src = record.image_path;
      imgBox.classList.remove('hidden');
    } else {
      imgBox.classList.add('hidden');
    }
  }

  // Load OCR revision history
  loadOCRRevisions(record.document_id, record.id);
}

async function loadOCRRevisions(docId, ocrId) {
  const container = document.getElementById('ocr-revision-list');
  if (!container) return;

  try {
    const data = await api.getOCRRevisions(docId, ocrId);
    if (!data.revisions || data.revisions.length === 0) {
      container.innerHTML = `<p class="text-gray-400 italic text-[10px]">No previous revisions recorded for this page.</p>`;
      return;
    }

    container.innerHTML = data.revisions.map(rev => `
      <div class="p-2 rounded bg-gray-50 border border-gray-200 space-y-1">
        <div class="flex justify-between font-bold text-[#141F39] text-[10px]">
          <span>Action: ${rev.action} by ${rev.changed_by || 'Archivist'}</span>
          <span class="text-gray-400 font-normal">${new Date(rev.created_at).toLocaleString()}</span>
        </div>
        ${rev.reason ? `<div class="text-[10px] text-amber-900 font-medium">Reason: ${rev.reason}</div>` : ''}
        <div class="text-[10px] text-gray-500 font-mono bg-white p-1 rounded border border-gray-100 truncate" title="${rev.new_text}">
          Text: ${rev.new_text.substring(0, 100)}...
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error("Failed to load OCR revisions:", e);
    container.innerHTML = `<p class="text-gray-400 italic text-[10px]">Unable to load revision history.</p>`;
  }
}

function clearOCRDisplay() {
  const titleEl = document.getElementById('ocr-record-title');
  const confEl = document.getElementById('ocr-record-conf');
  const textEl = document.getElementById('ocr-review-text');
  const imgBox = document.getElementById('ocr-facsimile-box');
  const updatedEl = document.getElementById('ocr-record-updated');
  const revList = document.getElementById('ocr-revision-list');

  if (titleEl) titleEl.textContent = "No record selected";
  if (confEl) confEl.textContent = "Confidence unavailable";
  if (textEl) textEl.value = "";
  if (imgBox) imgBox.classList.add('hidden');
  if (updatedEl) updatedEl.textContent = "-";
  if (revList) revList.innerHTML = `<p class="text-gray-400 italic">No record selected.</p>`;
}

async function handleDocumentUpload(e) {
  e.preventDefault();

  const fileInput = document.getElementById('upload-file');
  const title = document.getElementById('upload-title')?.value.trim();
  const author = document.getElementById('upload-author')?.value.trim();
  const type = document.getElementById('upload-type')?.value;
  const year = document.getElementById('upload-year')?.value;
  const lang = document.getElementById('upload-language')?.value;
  const collection = document.getElementById('upload-collection')?.value.trim();
  const institution = document.getElementById('upload-institution')?.value.trim();
  const provenance = document.getElementById('upload-provenance')?.value;
  const keywords = document.getElementById('upload-keywords')?.value.trim();
  const desc = document.getElementById('upload-description')?.value.trim();
  const edition = document.getElementById('upload-edition')?.value.trim();
  const volume = document.getElementById('upload-volume')?.value.trim();
  const pageCount = document.getElementById('upload-pagecount')?.value;
  const rights = document.getElementById('upload-rights')?.value.trim();

  const progressBox = document.getElementById('ingest-progress');
  const logText = document.getElementById('ingest-log-text');
  const submitBtn = document.getElementById('start-ingest-btn');
  const dupAlert = document.getElementById('duplicate-alert');
  const dupDocId = document.getElementById('dup-doc-id');
  const dupFilename = document.getElementById('dup-filename');
  const dupInspectBtn = document.getElementById('dup-inspect-btn');
  const batchSection = document.getElementById('batch-progress-section');
  const batchTbody = document.getElementById('batch-status-tbody');
  const batchSummary = document.getElementById('batch-summary-badge');

  if (dupAlert) dupAlert.classList.add('hidden');

  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    window.DAIC?.showToast("Please select at least one file.", "error");
    return;
  }

  const files = Array.from(fileInput.files);
  const allowed = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];

  // Validate all extensions upfront
  const invalid = files.filter(f => !allowed.includes(f.name.substring(f.name.lastIndexOf('.')).toLowerCase()));
  if (invalid.length > 0) {
    window.DAIC?.showToast(`Unsupported format for: ${invalid.map(f=>f.name).join(', ')}`, "error");
    return;
  }

  if (progressBox) progressBox.classList.remove('hidden');
  if (submitBtn) submitBtn.disabled = true;

  const isBatch = files.length > 1;

  if (!isBatch) {
    // Single file
    if (!title) {
      window.DAIC?.showToast("Please provide a document title.", "error");
      if (submitBtn) submitBtn.disabled = false;
      return;
    }

    const formData = new FormData();
    formData.append('file', files[0]);
    formData.append('title', title);
    formData.append('author', author || 'NOT PROVIDED');
    formData.append('doc_type', type || 'Manuscript');
    if (year) formData.append('year', parseInt(year));
    formData.append('language', lang || 'en');
    formData.append('collection', collection || 'Archival Ingestions');
    formData.append('source_institution', institution || 'NOT PROVIDED');
    formData.append('provenance_type', provenance || 'USER-UPLOADED DATA');
    if (keywords) formData.append('keywords', keywords);
    if (desc) formData.append('description', desc);
    if (edition) formData.append('edition', edition);
    if (volume) formData.append('volume', volume);
    if (pageCount) formData.append('page_count', parseInt(pageCount));
    if (rights) formData.append('rights', rights);

    if (logText) logText.innerHTML = `<div>• Uploading and preserving "${files[0].name}"...</div>
      <div>• Computing SHA-256 integrity hash & duplicate check...</div>
      <div>• Extracting pages & facsimiles via PyMuPDF...</div>`;

    try {
      const res = await api.uploadDocument(formData);

      if (res.status === 'duplicate') {
        // Display DUPLICATE DOCUMENT alert as required
        if (dupAlert) {
          dupAlert.classList.remove('hidden');
          if (dupDocId) dupDocId.textContent = res.existing_document_id || res.duplicate_of;
          if (dupFilename) dupFilename.textContent = res.existing_filename || files[0].name;
          if (dupInspectBtn) {
            dupInspectBtn.onclick = () => {
              window.location.href = `/manuscripts?doc=${encodeURIComponent(res.existing_document_id || res.duplicate_of)}`;
            };
          }
        }
        if (logText) {
          logText.innerHTML = `
            <div class="p-2 rounded bg-amber-100 text-amber-900 border border-amber-300 font-bold">
              DUPLICATE DOCUMENT DETECTED<br>
              Existing Document ID: ${res.existing_document_id || res.duplicate_of}<br>
              Existing filename: ${res.existing_filename || files[0].name}
            </div>
          `;
        }
        window.DAIC?.showToast(`Duplicate: already archived under ${res.existing_document_id || res.duplicate_of}`, "warning");
        await loadAdminStats();
        return;
      }

      window.DAIC?.showToast(`✓ Document preserved under ID ${res.document_id}!`);
      if (logText) logText.innerHTML += `<div class="text-green-700 font-bold mt-1">
        ✓ Complete! ID: <strong>${res.document_id}</strong><br>
        SHA-256: <span class="font-mono text-[10px]">${res.sha256_hash.substring(0,16)}...</span><br>
        Status: <strong>${res.verification_status}</strong> (${res.pages_processed} page(s) queued)
      </div>`;
      document.getElementById('upload-form').reset();
      await loadAdminStats();
      await loadPendingOCR(`ocr_${res.document_id}_p1`);
      await loadDocumentTable();
    } catch (err) {
      window.DAIC?.showToast(err.message || "Failed to ingest document", "error");
      if (logText) logText.innerHTML += `<div class="text-red-600 mt-1">Error: ${err.message}</div>`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }

  } else {
    // Batch upload
    if (logText) {
      logText.innerHTML = `<div class="font-bold">Batch ingestion: ${files.length} files processing...</div>`;
    }

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    formData.append('doc_type', type || 'Manuscript');
    if (year) formData.append('year', parseInt(year));
    formData.append('language', lang || 'en');
    formData.append('collection', collection || 'Archival Ingestions');
    formData.append('author', author || 'NOT PROVIDED');
    formData.append('source_institution', institution || 'NOT PROVIDED');
    formData.append('provenance_type', provenance || 'USER-UPLOADED DATA');
    if (desc) formData.append('description', desc);
    if (edition) formData.append('edition', edition);
    if (volume) formData.append('volume', volume);
    if (pageCount) formData.append('page_count', parseInt(pageCount));
    if (rights) formData.append('rights', rights);

    try {
      const batchRes = await api.uploadBatch(formData);

      // Render Batch Progress Table
      if (batchSection && batchTbody) {
        batchSection.classList.remove('hidden');
        if (batchSummary) {
          batchSummary.textContent = `✓ ${batchRes.successful} Success / ⚠ ${batchRes.duplicates} Duplicates / ✗ ${batchRes.failed} Errors`;
        }

        batchTbody.innerHTML = batchRes.results.map(r => {
          let statusBadge = '';
          if (r.status === 'success') {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">OCR REVIEW</span>`;
          } else if (r.status === 'DUPLICATE') {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900">DUPLICATE</span>`;
          } else if (r.status === 'UNSUPPORTED_FORMAT') {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800">UNSUPPORTED</span>`;
          } else {
            statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800">ERROR</span>`;
          }

          return `
            <tr class="border-b border-gray-100 hover:bg-gray-50">
              <td class="px-3 py-1.5 font-medium text-gray-800">${r.filename}</td>
              <td class="px-3 py-1.5">${statusBadge}</td>
              <td class="px-3 py-1.5 font-mono font-bold text-[#141F39]">${r.document_id || (r.duplicate_of ? `(dup of ${r.duplicate_of})` : '-')}</td>
              <td class="px-3 py-1.5 text-center">${r.pages_processed || '-'}</td>
              <td class="px-3 py-1.5 text-[10px] text-gray-500">
                ${r.error ? `<span class="text-red-600">${r.error}</span>` : ''}
                ${r.duplicate_of ? `<a href="/manuscripts?doc=${encodeURIComponent(r.duplicate_of)}" class="text-[#D7A940] underline font-bold">Inspect Existing</a>` : ''}
                ${r.document_id ? `<span class="text-green-700">Ready for Review</span>` : ''}
              </td>
            </tr>
          `;
        }).join('');
      }

      const firstSuccess = batchRes.results.find(r => r.status === 'success');
      window.DAIC?.showToast(`Batch completed: ${batchRes.successful} ingested, ${batchRes.duplicates} duplicates, ${batchRes.failed} failed.`);
      document.getElementById('upload-form').reset();
      await loadAdminStats();
      await loadPendingOCR(firstSuccess ? `ocr_${firstSuccess.document_id}_p1` : null);
      await loadDocumentTable();

    } catch (err) {
      window.DAIC?.showToast(err.message || "Batch upload failed", "error");
      if (logText) logText.innerHTML += `<div class="text-red-600 mt-1">Error: ${err.message}</div>`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }
}

async function dispatchOCRReview(newStatus) {
  if (!currentSelectedOCR) {
    window.DAIC?.showToast("Please select a document page to review.", "error");
    return;
  }

  const textEl = document.getElementById('ocr-review-text');
  const notesEl = document.getElementById('ocr-review-notes');
  const reasonEl = document.getElementById('ocr-review-reason');
  const text = textEl ? textEl.value.trim() : "";
  const notes = notesEl ? notesEl.value.trim() : "";
  const reason = reasonEl ? reasonEl.value.trim() : "";

  if (!text && newStatus !== 'rejected') {
    window.DAIC?.showToast("OCR text cannot be empty.", "error");
    return;
  }

  try {
    const res = await api.reviewOCR({
      ocr_id: currentSelectedOCR.id,
      recognized_text: text || currentSelectedOCR.recognized_text,
      status: newStatus,
      notes: notes || (newStatus === 'verified' ? "Verified by Chief Archivist" : newStatus === 'rejected' ? "Rejected by Archivist" : "Reviewed and corrected"),
      reason: reason || (newStatus === 'verified' ? "Archivist human verification" : newStatus === 'rejected' ? "Archivist rejection" : "Correction edit"),
      changed_by: "Chief Archivist"
    });

    if (newStatus === 'verified') {
      window.DAIC?.showToast(`✓ Page verified! Indexed ${res.chunks_indexed} chunk(s) into FTS5 & FAISS.`);
    } else if (newStatus === 'rejected') {
      window.DAIC?.showToast("✗ Page marked as Rejected.");
    } else if (newStatus === 'pending_review') {
      window.DAIC?.showToast("↺ Page returned to Pending Review queue.");
    } else {
      window.DAIC?.showToast("✓ Corrections saved as Archivist Reviewed.");
    }

    if (reasonEl) reasonEl.value = "";
    await loadAdminStats();
    await loadPendingOCR(currentSelectedOCR.id);
    await loadOCRRevisions(currentSelectedOCR.document_id, currentSelectedOCR.id);
    await loadDocumentTable();

  } catch (e) {
    window.DAIC?.showToast(e.message || "Error updating OCR record", "error");
  }
}

// ─────────────────────────────────────────────────────────────
// Document Ingestion Table
// ─────────────────────────────────────────────────────────────
async function loadDocumentTable() {
  const container = document.getElementById('doc-ingestion-table');
  if (!container) return;

  try {
    const data = await api.getAdminDocuments(100);
    if (!data.documents || data.documents.length === 0) {
      container.innerHTML = `<p class="text-xs text-gray-400 italic p-3">No documents found.</p>`;
      return;
    }

    const provenanceColor = (p) => {
      if (p === 'USER-UPLOADED DATA') return 'bg-blue-100 text-blue-800';
      if (p === 'REAL ARCHIVAL DATA') return 'bg-emerald-100 text-emerald-800';
      if (p === 'DEMO DATA') return 'bg-amber-100 text-amber-800';
      return 'bg-gray-100 text-gray-700';
    };
    const ocrColor = (s) => {
      if (s === 'verified') return 'text-green-700';
      if (s === 'pending_review') return 'text-amber-700';
      return 'text-gray-500';
    };
    const verColor = (v) => {
      if (v === 'VERIFIED SOURCE') return 'text-green-700 font-bold';
      if (v === 'UNVERIFIED (NEW INGESTION)') return 'text-amber-600';
      return 'text-gray-500';
    };

    container.innerHTML = `
      <table class="w-full text-[10px] border-collapse">
        <thead>
          <tr class="bg-[#141F39] text-[#D7A940] text-left">
            <th class="px-2 py-1.5 font-bold">Doc ID</th>
            <th class="px-2 py-1.5 font-bold">Filename</th>
            <th class="px-2 py-1.5 font-bold">Type</th>
            <th class="px-2 py-1.5 font-bold">Provenance</th>
            <th class="px-2 py-1.5 font-bold">OCR Status</th>
            <th class="px-2 py-1.5 font-bold">Verification</th>
            <th class="px-2 py-1.5 font-bold">Pages</th>
            <th class="px-2 py-1.5 font-bold">Chunks</th>
          </tr>
        </thead>
        <tbody>
          ${data.documents.map((d, i) => `
            <tr class="${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} border-b border-gray-100 hover:bg-[#FFF6E5] transition-colors">
              <td class="px-2 py-1.5 font-mono font-bold text-[#141F39]">${d.id}</td>
              <td class="px-2 py-1.5 text-gray-600 max-w-[140px] truncate" title="${d.original_filename || d.title}">${d.original_filename || d.title || '-'}</td>
              <td class="px-2 py-1.5 text-gray-500">${d.type || '-'}</td>
              <td class="px-2 py-1.5"><span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${provenanceColor(d.provenance_type)}">${d.provenance_type || '-'}</span></td>
              <td class="px-2 py-1.5 ${ocrColor(d.ocr_status)} font-mono">${d.ocr_status || '-'}</td>
              <td class="px-2 py-1.5 ${verColor(d.verification_status)}">${d.verification_status === 'VERIFIED SOURCE' ? '✓ VERIFIED' : d.verification_status === 'UNVERIFIED (NEW INGESTION)' ? 'UNVERIFIED' : d.verification_status || '-'}</td>
              <td class="px-2 py-1.5 text-center text-gray-600">${d.page_count || '-'}</td>
              <td class="px-2 py-1.5 text-center font-bold ${d.chunk_count > 0 ? 'text-[#3B7558]' : 'text-gray-400'}">${d.chunk_count ?? '-'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      <p class="text-[10px] text-gray-400 mt-2 px-2">Showing ${data.documents.length} of ${data.total} documents.</p>
    `;
  } catch (e) {
    console.error("Failed to load document table:", e);
    container.innerHTML = `<p class="text-xs text-red-500 p-3">Failed to load document table.</p>`;
  }
}



