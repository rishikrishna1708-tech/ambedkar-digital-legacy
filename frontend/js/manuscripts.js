/**
 * Ambedkar Digital Legacy - Manuscript & OCR Viewer Controller
 * Manages preserved manuscript catalogue cards, synchronized facsimile viewing,
 * and high-confidence OCR text comparison.
 */

let currentZoom = 1.0;
let isComparing = false;
let activeManuscriptKey = "MAHAD_SATYAGRAHA_1927";

const MANUSCRIPT_PRESETS = {
  "MAHAD_SATYAGRAHA_1927": {
    key: "MAHAD_SATYAGRAHA_1927",
    title: "Chavdar Tale Proclamation & Satyagraha Declaration",
    shortTitle: "CHAVDAR TALE PROCLAMATION (1927)",
    date: "20 March 1927",
    collection: "Historical Records & Manuscripts",
    language: "Marathi / English",
    ocrStatus: "PaddleOCR Recognized (94.8%)",
    verificationStatus: "Verified by Chief Archivist",
    institution: "Maharashtra State Archives",
    docId: "MAHAD_SATYAGRAHA_1927",
    page: 4,
    totalPages: 18,
    facsimileText: "We are not going to the Chavdar Tank merely to drink water. We are going to the tank to assert that we too are human beings like others. It must be clearly understood that this struggle is not for water alone, but for fundamental human equality.",
    citation: "Bahishkrit Hitakarini Sabha Records",
    confidence: "94.8%"
  },
  "CAD_VOL_07_ART17": {
    key: "CAD_VOL_07_ART17",
    title: "Constituent Assembly Drafting: Abolition of Untouchability (Draft Art. 11 / Art. 17)",
    shortTitle: "CONSTITUENT ASSEMBLY: DRAFT ARTICLE 11",
    date: "29 November 1948",
    collection: "Constituent Assembly Debates Archive",
    language: "English",
    ocrStatus: "PaddleOCR Recognized (96.4%)",
    verificationStatus: "Parliamentary Authenticated",
    institution: "Parliament Library of India",
    docId: "CAD_VOL_07_ART17",
    page: 653,
    totalPages: 820,
    facsimileText: "'Untouchability' is abolished and its practice in any form is forbidden. The enforcement of any disability arising out of 'Untouchability' shall be an offence punishable in accordance with law.",
    citation: "CAD Vol. VII Proceedings, 29 Nov 1948",
    confidence: "96.4%"
  },
  "BAWS_VOL_10_LABOUR": {
    key: "BAWS_VOL_10_LABOUR",
    title: "Standing Labour Committee: Reduction of Working Hours to 8 Hours",
    shortTitle: "7TH INDIAN LABOUR CONFERENCE: 8-HOUR WORKDAY",
    date: "27 November 1942",
    collection: "Writings and Speeches",
    language: "English",
    ocrStatus: "PaddleOCR Recognized (95.1%)",
    verificationStatus: "Curatorial Authenticated",
    institution: "Dr. Ambedkar Foundation / AIC",
    docId: "BAWS_VOL_10_LABOUR",
    page: 85,
    totalPages: 560,
    facsimileText: "Labour legislation is not a concession but an inherent social right essential for human dignity. Daily working hours shall be reduced from 12 hours to 8 hours across industrial establishments.",
    citation: "Standing Labour Committee Resolution",
    confidence: "95.1%"
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  renderManuscriptCatalog();
  switchManuscript(activeManuscriptKey);
  await loadDynamicManuscripts();
});

async function loadDynamicManuscripts() {
  try {
    const archiveData = await api.getArchive({ limit: 50 });
    const docs = archiveData.documents || [];
    
    for (const d of docs) {
      if (d.id && (d.id.startsWith("ADL-MS-") || d.type === "Manuscript")) {
        const ocrData = await api.getPendingOCR(d.id).catch(() => ({ records: [] }));
        const records = ocrData.records || [];
        const firstRecord = records[0] || {};

        let confStr = "Confidence unavailable";
        if (firstRecord.confidence !== null && firstRecord.confidence !== undefined) {
          confStr = `${(firstRecord.confidence * 100).toFixed(1)}%`;
        }

        MANUSCRIPT_PRESETS[d.id] = {
          key: d.id,
          title: d.title,
          shortTitle: (d.title || '').toUpperCase(),
          date: d.date_str || (d.year ? d.year.toString() : 'Historical'),
          collection: d.collection || 'Archival Ingestions',
          language: d.language === 'mr' ? 'Marathi' : (d.language === 'hi' ? 'Hindi' : 'English'),
          ocrStatus: d.ocr_status === 'verified' ? `Verified Archivist OCR` : `Candidate OCR (${confStr})`,
          verificationStatus: d.verification_status || 'UNVERIFIED (NEW INGESTION)',
          provenanceType: d.provenance_type || 'USER-UPLOADED DATA',
          institution: d.source_institution || 'Archival Preservation Repository',
          docId: d.id,
          page: firstRecord.page || 1,
          totalPages: d.page_count || 1,
          facsimileImg: firstRecord.image_path || (d.source_url && d.source_url.endsWith('.png') ? d.source_url : null),
          facsimileText: firstRecord.recognized_text || d.summary || 'Archival manuscript text extract.',
          citation: `${d.title}, Institution: ${d.source_institution || 'Preserved Archive'}`,
          confidence: confStr
        };
      }
    }

    renderManuscriptCatalog();

    // Check if query param requests a specific doc
    const params = new URLSearchParams(window.location.search);
    const reqDoc = params.get('doc');
    if (reqDoc && MANUSCRIPT_PRESETS[reqDoc]) {
      focusManuscript(reqDoc, 'facsimile');
    }
  } catch (err) {
    console.error("Could not dynamically load ingested manuscripts:", err);
  }
}

function renderManuscriptCatalog() {
  const container = document.getElementById('manuscript-catalog-cards');
  if (!container) return;

  const items = Object.values(MANUSCRIPT_PRESETS);
  container.innerHTML = items.map(m => `
    <div class="archival-card p-5 rounded-lg flex flex-col justify-between text-xs space-y-4 ${m.key === activeManuscriptKey ? 'border-2 border-[#D7A940]' : ''}">
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-[#141F39] uppercase">
            ${m.collection}
          </span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded ${m.verificationStatus === 'VERIFIED SOURCE' ? 'text-[#3B7558] bg-[#E8F3ED]' : 'text-amber-800 bg-amber-100'}">
            ✓ ${m.verificationStatus}
          </span>
        </div>

        <h3 class="font-heading-cinzel font-bold text-sm text-[#141F39] leading-snug">
          ${m.title}
        </h3>

        <div class="space-y-1 text-gray-600 text-[11px] pt-1">
          <div><strong>ID:</strong> <span class="font-mono text-[#141F39] font-bold">${m.docId}</span></div>
          <div><strong>Date:</strong> ${m.date}</div>
          <div><strong>Language:</strong> ${m.language}</div>
          <div><strong>OCR Status:</strong> <span class="font-medium">${m.ocrStatus}</span></div>
          <div><strong>Source:</strong> ${m.institution}</div>
        </div>
      </div>

      <!-- Action Buttons matching spec: VIEW MANUSCRIPT, VIEW OCR, SEARCH TEXT, SOURCE -->
      <div class="pt-3 border-t border-gray-100 flex flex-wrap gap-1.5">
        <button onclick="focusManuscript('${m.key}', 'facsimile')" class="px-2.5 py-1 bg-[#141F39] text-[#D7A940] rounded font-semibold text-[11px] hover:bg-[#202E4E] transition-colors border border-[#D7A940]">
          VIEW MANUSCRIPT
        </button>
        <button onclick="focusManuscript('${m.key}', 'ocr')" class="px-2.5 py-1 bg-gray-100 text-[#141F39] rounded font-semibold text-[11px] hover:bg-gray-200 transition-colors border border-gray-300">
          VIEW OCR
        </button>
        <a href="/ask?q=Tell%20me%20about%20${encodeURIComponent(m.title)}" class="px-2.5 py-1 bg-[#FBF4E2] text-[#8C5B08] rounded font-semibold text-[11px] hover:bg-[#F4E8C1] transition-colors">
          SEARCH TEXT
        </a>
        <button onclick="DAIC.openOriginalDocument('${m.docId}', ${m.page})" class="px-2.5 py-1 text-gray-600 hover:text-black font-semibold text-[11px] underline">
          SOURCE
        </button>
      </div>
    </div>
  `).join('');
}

function focusManuscript(key, mode = 'facsimile') {
  activeManuscriptKey = key;
  switchManuscript(key);
  renderManuscriptCatalog();

  const viewer = document.getElementById('viewer-container');
  if (viewer) {
    viewer.scrollIntoView({ behavior: 'smooth' });
  }

  if (mode === 'ocr') {
    const ocrPane = document.getElementById('ocr-pane');
    if (ocrPane) {
      ocrPane.classList.add('ring-2', 'ring-[#D7A940]');
      setTimeout(() => ocrPane.classList.remove('ring-2', 'ring-[#D7A940]'), 1500);
    }
  }
}

function adjustZoom(delta) {
  currentZoom = Math.min(1.8, Math.max(0.6, currentZoom + delta));
  const canvas = document.getElementById('facsimile-canvas');
  const txt = document.getElementById('zoom-level-text');
  if (canvas) canvas.style.transform = `scale(${currentZoom})`;
  if (txt) txt.textContent = `${Math.round(currentZoom * 100)}%`;
}

function switchManuscript(key) {
  activeManuscriptKey = key;
  const m = MANUSCRIPT_PRESETS[key];
  if (!m) return;

  const pageBadge = document.getElementById('manuscript-page-badge');
  if (pageBadge) pageBadge.textContent = `Page ${m.page} of ${m.totalPages}`;

  const confidenceBadge = document.getElementById('ocr-confidence-badge');
  if (confidenceBadge) confidenceBadge.textContent = `Confidence: ${m.confidence}`;

  const canvas = document.getElementById('facsimile-canvas');
  if (canvas) {
    if (m.facsimileImg) {
      canvas.innerHTML = `
        <div class="border-b border-[#A68F74] pb-2 text-center text-xs tracking-widest uppercase font-bold text-[#4A3B2C]">
          ${m.institution} • Preserved Archival Facsimile
        </div>
        <div class="py-3 text-center">
          <img src="${m.facsimileImg}" alt="Facsimile" class="max-h-[500px] mx-auto rounded shadow-sm object-contain border border-[#D5C7B0]">
        </div>
        <div class="pt-2 text-right text-[10px] text-[#5C4D3E]">
          — ${m.citation}
        </div>
      `;
    } else {
      canvas.innerHTML = `
        <div class="border-b border-[#A68F74] pb-2 text-center text-xs tracking-widest uppercase font-bold text-[#4A3B2C]">
          ${m.institution} • Historical Record
        </div>
        <div class="py-4 space-y-3 text-xs leading-relaxed italic text-[#2A231D]">
          <p class="font-bold text-center not-italic text-sm text-[#141F39]">${m.shortTitle}</p>
          <p>"${m.facsimileText}"</p>
          <div class="pt-4 text-right text-[10px] text-[#5C4D3E]">
            — ${m.citation}
          </div>
        </div>
      `;
    }
  }

  const ocrBlocks = document.getElementById('ocr-text-blocks');
  if (ocrBlocks) {
    ocrBlocks.innerHTML = `
      <div class="p-2.5 rounded bg-white border border-gray-200 space-y-1">
        <div class="flex justify-between text-[10px] text-gray-400 font-mono">
          <span>Record ID: [${m.docId}]</span>
          <span class="text-green-700 font-bold">${m.confidence}</span>
        </div>
        <div class="font-sans font-bold text-[#141F39]">${m.shortTitle}</div>
      </div>

      <div class="p-2.5 rounded bg-white border border-gray-200 space-y-1">
        <div class="flex justify-between text-[10px] text-gray-400 font-mono">
          <span>Page ${m.page} Transcription</span>
          <span class="text-[#3B7558] font-bold">${m.verificationStatus}</span>
        </div>
        <div class="font-sans text-gray-800 leading-relaxed whitespace-pre-line">
          ${m.facsimileText}
        </div>
      </div>

      <div class="p-2.5 rounded bg-white border border-gray-200 space-y-1">
        <div class="flex justify-between text-[10px] text-gray-400 font-mono">
          <span>Archival Provenance</span>
          <span class="text-gray-500 font-mono text-[10px]">${m.docId}</span>
        </div>
        <div class="font-sans text-gray-600">
          — ${m.citation}
        </div>
      </div>
    `;
  }

  // Update Dossier
  const dInst = document.getElementById('dossier-inst');
  const dColl = document.getElementById('dossier-coll');
  const dId = document.getElementById('dossier-id');
  if (dInst) dInst.textContent = m.institution;
  if (dColl) dColl.textContent = m.collection;
  if (dId) dId.textContent = m.docId;
}

function toggleCompareOverlay() {
  isComparing = !isComparing;
  const canvas = document.getElementById('facsimile-canvas');
  const btn = document.getElementById('compare-btn');
  if (!canvas || !btn) return;

  if (isComparing) {
    btn.classList.add('bg-[#D7A940]', 'text-[#141F39]', 'font-bold');
    btn.textContent = "Exit Comparison Mode";
    canvas.classList.add('ring-4', 'ring-[#3B7558]/50');
    window.DAIC.showToast("Comparing OCR transcription overlays with manuscript facsimile.");
  } else {
    btn.classList.remove('bg-[#D7A940]', 'text-[#141F39]', 'font-bold');
    btn.textContent = "Compare Original / OCR";
    canvas.classList.remove('ring-4', 'ring-[#3B7558]/50');
  }
}

function saveActiveOcrToResearch() {
  const m = MANUSCRIPT_PRESETS[activeManuscriptKey];
  if (!m) return;
  window.DAIC.addToResearch(
    `${m.shortTitle} (OCR Transcript)`,
    m.facsimileText,
    m.page,
    m.docId,
    null,
    m.collection
  );
}
