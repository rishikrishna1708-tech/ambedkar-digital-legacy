/**
 * Ambedkar Digital Legacy - Ask / AI Research Assistant Controller
 * Provides strictly grounded archival inquiry with hybrid FTS5 + FAISS retrieval,
 * Evidence Gate verification, institutional citation rendering, and complete
 * multilingual voice input and audio narration controls.
 */

let currentAnswerData = null;
let isDebugVisible = false;

document.addEventListener('DOMContentLoaded', () => {
  initAskPage();
});

function initAskPage() {
  const form = document.getElementById('ask-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('question-input');
      if (input && input.value.trim()) {
        executeAsk(input.value.trim());
      }
    });
  }

  // Check URL query parameter (e.g., /ask?q=...)
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  if (q) {
    const input = document.getElementById('question-input');
    if (input) input.value = q;
    executeAsk(q);
  }

  // Listen to speech synthesis state updates to sync UI buttons
  window.addEventListener('daic:speechStateChanged', (e) => {
    updateAudioControlsUI(e.detail.state);
  });

  // Listen to language changes to update voice input indicator if visible
  window.addEventListener('daic:languageChanged', (e) => {
    const langInfo = e.detail.langInfo;
    const ind = document.getElementById('voice-lang-indicator');
    if (ind && langInfo) {
      ind.textContent = `Listening — ${langInfo.native}`;
    }
  });
}

function setQuery(query) {
  const input = document.getElementById('question-input');
  if (input) {
    input.value = query;
    executeAsk(query);
  }
}

function toggleDebugPanel() {
  isDebugVisible = !isDebugVisible;
  const panel = document.getElementById('retrieval-debug-panel');
  const btnText = document.getElementById('debug-btn-text');
  if (panel) {
    if (isDebugVisible) {
      panel.classList.remove('hidden');
      btnText.textContent = "Hide Retrieval Trace";
    } else {
      panel.classList.add('hidden');
      btnText.textContent = "Archival Retrieval Trace (RRF / FAISS / FTS5)";
    }
  }
}

async function executeAsk(question) {
  const welcomeCard = document.getElementById('welcome-research-card');
  const stepsCard = document.getElementById('retrieval-steps-card');
  const answerCard = document.getElementById('answer-card');
  const submitBtn = document.getElementById('submit-ask-btn');
  const insufficientNotice = document.getElementById('insufficient-evidence-notice');

  if (welcomeCard) welcomeCard.classList.add('hidden');
  if (answerCard) answerCard.classList.add('hidden');
  if (stepsCard) stepsCard.classList.remove('hidden');
  if (submitBtn) submitBtn.disabled = true;

  resetRetrievalSteps();

  const startTime = Date.now();
  const timerInterval = setInterval(() => {
    const el = document.getElementById('retrieval-elapsed-time');
    if (el) el.textContent = `${Date.now() - startTime}ms`;
  }, 50);

  try {
    // Step 1: Lexical
    setStepActive('step-fts');
    await delay(120);

    // Step 2: Dense
    setStepActive('step-faiss');
    await delay(120);

    // Step 3: RRF
    setStepActive('step-rrf');
    await delay(100);

    // API Call
    const result = await api.ask(question, window.DAIC.currentLanguage);
    currentAnswerData = result;

    // Step 4: Rerank
    setStepActive('step-rerank');
    await delay(80);

    // Step 5: Evidence Gate
    setStepActive('step-gate');
    await delay(80);

    // Step 6: Synthesis
    setStepActive('step-synthesis');
    await delay(80);

    clearInterval(timerInterval);
    const finalElapsed = document.getElementById('retrieval-elapsed-time');
    if (finalElapsed && result.retrieval) {
      finalElapsed.textContent = `${result.retrieval.latency_ms || (Date.now() - startTime)}ms`;
    }

    // Render Grounded Answer & Sources
    renderAnswer(result);
    renderSources(result.sources || [], result.evidence || []);
    renderDebugTrace(result);

  } catch (err) {
    clearInterval(timerInterval);
    console.error("Ask error:", err);
    window.DAIC.showToast(err.message || "Archival retrieval error", "error");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function resetRetrievalSteps() {
  const stepIds = ['step-fts', 'step-faiss', 'step-rrf', 'step-rerank', 'step-gate', 'step-synthesis'];
  stepIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.className = 'p-2 rounded bg-gray-50 border border-gray-200 flex items-center space-x-2 text-gray-400';
      const ind = el.querySelector('.status-indicator');
      if (ind) ind.className = 'status-indicator w-2 h-2 rounded-full bg-gray-400';
    }
  });
}

function setStepActive(id) {
  const el = document.getElementById(id);
  if (el) {
    el.className = 'p-2 rounded bg-[#FAF8F1] border border-[#D7A940] flex items-center space-x-2 text-[#141F39] font-medium shadow-sm';
    const ind = el.querySelector('.status-indicator');
    if (ind) ind.className = 'status-indicator w-2 h-2 rounded-full bg-[#3B7558]';
  }
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function renderAnswer(result) {
  const answerCard = document.getElementById('answer-card');
  const answerText = document.getElementById('answer-text');
  const badge = document.getElementById('evidence-status-badge');
  const insufficientNotice = document.getElementById('insufficient-evidence-notice');

  if (!answerCard || !answerText) return;

  answerCard.classList.remove('hidden');

  if (result.verified) {
    badge.className = 'badge-verified text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center space-x-1';
    badge.innerHTML = `<span>✓ Verified Archival Evidence</span>`;
    if (insufficientNotice) insufficientNotice.classList.add('hidden');
  } else {
    badge.className = 'badge-insufficient text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center space-x-1';
    badge.innerHTML = `<span>⚠ Evidence Insufficient</span>`;
    if (insufficientNotice) insufficientNotice.classList.remove('hidden');
  }

  // Format markdown paragraphs
  const raw = result.answer || "";
  const paragraphs = raw.split('\n\n').filter(p => p.trim());
  const formattedHtml = paragraphs.map(p => {
    let clean = p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                 .replace(/\*(.*?)\*/g, '<em>$1</em>');
    if (clean.startsWith('>')) {
      clean = `<blockquote class="border-l-4 border-[#D7A940] pl-3 py-1 bg-[#FAF8F1] rounded font-serif-archival italic text-gray-800">${clean.substring(1).trim()}</blockquote>`;
    } else {
      clean = `<p class="text-gray-800 leading-relaxed">${clean}</p>`;
    }
    return clean;
  }).join('');

  answerText.innerHTML = formattedHtml;
}

function renderSources(sources, evidence) {
  const container = document.getElementById('sources-container');
  const countBadge = document.getElementById('sources-count-badge');
  if (!container) return;

  const count = sources.length;
  if (countBadge) countBadge.textContent = `${count} Source${count === 1 ? '' : 's'}`;

  if (count === 0) {
    container.innerHTML = `
      <div class="text-center py-6 text-gray-400 text-xs">
        <p>No verified sources satisfied the archival threshold for this inquiry.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = sources.map((s, idx) => `
    <div class="archival-card p-3.5 rounded border border-[#E8E2D2] text-xs space-y-2.5">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-bold text-[#8C5B08] uppercase tracking-wider bg-[#FFF6E5] px-1.5 py-0.5 rounded border border-[#F5D399]">
          PRIMARY SOURCE #${idx + 1}
        </span>
        <span class="text-[10px] font-bold ${s.relevance_percent >= 80 ? 'text-[#3B7558]' : 'text-gray-600'}">
          Relevance: ${s.relevance_percent || 95}%
        </span>
      </div>

      <div class="space-y-1">
        <div>
          <span class="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">DOCUMENT</span>
          <h4 class="font-bold text-[#141F39] text-xs leading-snug">${s.title}</h4>
        </div>
        
        <div class="flex items-center space-x-2 pt-0.5">
          <span class="text-[10px] font-semibold bg-[#FBF4E2] text-[#8C5B08] px-1.5 py-0.5 rounded">
            PAGE ${s.page}
          </span>
          <span class="text-[10px] text-gray-500 truncate">
            <strong>COLLECTION:</strong> ${s.collection}
          </span>
        </div>
      </div>

      <div class="bg-[#FAF8F1] p-2.5 rounded border border-gray-100 font-serif-archival italic text-[11px] text-gray-800">
        <span class="text-[9px] uppercase not-italic text-gray-500 font-bold block mb-1">EVIDENCE QUOTE</span>
        "${s.evidence_snippet}"
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-gray-100">
        <button onclick="DAIC.openOriginalDocument('${s.document_id}', ${s.page})" class="px-2.5 py-1 bg-[#141F39] text-[#D7A940] rounded text-[11px] font-semibold hover:bg-[#202E4E] transition-colors flex items-center space-x-1">
          <span>Open Document</span>
        </button>
        <button onclick="DAIC.addToResearch('${s.title.replace(/'/g, "\\'")}', '${s.evidence_snippet.replace(/'/g, "\\'")}', ${s.page}, '${s.document_id}', null, '${s.collection.replace(/'/g, "\\'")}')" class="text-[11px] text-[#B88B28] font-bold hover:underline">
          + Add to Research
        </button>
      </div>
    </div>
  `).join('');
}

function renderDebugTrace(result) {
  const panel = document.getElementById('retrieval-debug-panel');
  if (!panel || !result.explainability) return;

  const exp = result.explainability;
  const stages = exp.stages || {};

  const summary = document.getElementById('debug-pipeline-summary');
  if (summary) {
    summary.textContent = `QUERY "${result.retrieval.query}" → FTS5 (${stages.fts_count}) + FAISS (${stages.dense_count}) → RRF FUSED (${stages.rrf_candidates_count}) → RE-RANKED (${stages.reranked_count}) → EVIDENCE GATE (${stages.verified_evidence_count}) → SYNTHESIZED`;
  }

  // FTS5 items
  const ftsList = document.getElementById('debug-fts-list');
  const ftsCount = document.getElementById('debug-fts-count');
  if (ftsList && exp.fts_results) {
    ftsCount.textContent = `${exp.fts_results.length} matches`;
    ftsList.innerHTML = exp.fts_results.map((r, i) => `
      <div class="p-1.5 bg-gray-50 rounded border border-gray-200">
        <div class="font-bold text-[#141F39]">#${i+1} ${r.title} (Page ${r.page})</div>
        <div class="text-gray-500">BM25 Rank: ${r.fts_rank} | Score: ${r.score.toFixed(3)}</div>
        <div class="truncate text-gray-400 mt-0.5">${r.content.substring(0, 80)}...</div>
      </div>
    `).join('');
  }

  // FAISS items
  const denseList = document.getElementById('debug-dense-list');
  const denseCount = document.getElementById('debug-dense-count');
  if (denseList && exp.dense_results) {
    denseCount.textContent = `${exp.dense_results.length} matches`;
    denseList.innerHTML = exp.dense_results.map((r, i) => `
      <div class="p-1.5 bg-gray-50 rounded border border-gray-200">
        <div class="font-bold text-[#141F39]">#${i+1} ${r.title} (Page ${r.page})</div>
        <div class="text-gray-500">Dense Rank: ${r.dense_rank} | DotProd: ${r.score.toFixed(3)}</div>
        <div class="truncate text-gray-400 mt-0.5">${r.content.substring(0, 80)}...</div>
      </div>
    `).join('');
  }

  // RRF & Rerank items
  const rrfList = document.getElementById('debug-rrf-list');
  const rrfCount = document.getElementById('debug-rrf-count');
  if (rrfList && exp.reranked_results) {
    rrfCount.textContent = `${exp.reranked_results.length} verified candidates`;
    rrfList.innerHTML = exp.reranked_results.map((r, i) => `
      <div class="p-2 bg-gray-50 rounded border ${r.db_verified ? 'border-green-300' : 'border-gray-200'}">
        <div class="flex justify-between items-center">
          <span class="font-bold text-[#141F39]">Candidate #${i+1}: ${r.title}</span>
          <span class="font-mono text-green-700 font-bold">RRF: ${r.rrf_score.toFixed(4)} | Rerank: ${r.rerank_score}</span>
        </div>
        <div class="text-gray-500 mt-0.5">Matched via: [${(r.matched_modes || []).join(', ')}] | Status: ${r.relevance_label}</div>
        <div class="text-gray-700 italic mt-1 font-serif-archival">"${r.content.substring(0, 140)}..."</div>
      </div>
    `).join('');
  }
}

// Audio Narration Controller
function playAnswerAudio() {
  if (!currentAnswerData || !currentAnswerData.answer) {
    window.DAIC.showToast("No answer text to narrate", "info");
    return;
  }
  const clean = currentAnswerData.answer.replace(/[*_#>`]/g, '');
  window.DAIC.speakText(clean);
}

function updateAudioControlsUI(state) {
  const playBtn = document.getElementById('answer-play-btn');
  const pauseBtn = document.getElementById('answer-pause-btn');

  if (!playBtn || !pauseBtn) return;

  if (state === 'playing') {
    playBtn.textContent = '▶ Playing';
    playBtn.classList.add('bg-[#3B7558]', 'text-white');
    playBtn.classList.remove('bg-[#141F39]', 'text-[#D7A940]');
    pauseBtn.textContent = 'Ⅱ Pause';
  } else if (state === 'paused') {
    playBtn.textContent = '▶ Resume';
    playBtn.classList.remove('bg-[#3B7558]', 'text-white');
    playBtn.classList.add('bg-[#141F39]', 'text-[#D7A940]');
    pauseBtn.textContent = '▶ Resume';
  } else {
    playBtn.textContent = '▶ Play';
    playBtn.classList.remove('bg-[#3B7558]', 'text-white');
    playBtn.classList.add('bg-[#141F39]', 'text-[#D7A940]');
    pauseBtn.textContent = 'Ⅱ Pause';
  }
}

function saveAnswerToResearch() {
  if (!currentAnswerData) return;
  window.DAIC.addToResearch(
    `Synthesis: ${currentAnswerData.retrieval.query}`,
    currentAnswerData.answer.substring(0, 300) + '...',
    null,
    null,
    null,
    "Ambedkar Digital Legacy Archival Synthesis"
  );
}

async function submitFeedback(rating) {
  if (!currentAnswerData) return;
  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: currentAnswerData.retrieval.query,
        rating: rating,
        comments: rating > 0 ? "Verified by user" : "Reported as insufficient"
      })
    });
    window.DAIC.showToast(rating > 0 ? "Thank you for confirming archival accuracy." : "Feedback recorded. Curators will review.");
  } catch (e) {
    window.DAIC.showToast("Feedback error", "error");
  }
}

// Multilingual Voice Input Controller
function toggleVoiceInput() {
  if (window.DAIC.recognitionState === 'listening') {
    stopVoiceInput();
  } else {
    startVoiceInputSession();
  }
}

function startVoiceInputSession() {
  const banner = document.getElementById('voice-listening-banner');
  const transcriptEl = document.getElementById('voice-live-transcript');
  const langIndicator = document.getElementById('voice-lang-indicator');
  const inputEl = document.getElementById('question-input');

  const currentLang = window.DAIC.currentLanguage || 'en';
  const langInfo = window.DAIC.VOICE_LANG_MAP[currentLang] || { native: 'English' };

  if (banner) banner.classList.remove('hidden');
  if (langIndicator) langIndicator.textContent = `Listening — ${langInfo.native}`;
  if (transcriptEl) transcriptEl.textContent = "Speak your archival inquiry...";

  window.DAIC.startVoiceInput({
    onStateChange: (state, info) => {
      const btn = document.getElementById('voice-input-btn');
      const micStatus = document.getElementById('mic-status-text');

      if (state === 'listening') {
        if (btn) btn.classList.add('bg-red-100', 'text-red-700', 'border-red-400');
        if (micStatus) micStatus.textContent = "Listening...";
      } else if (state === 'completed' || state === 'idle' || state === 'error') {
        if (btn) btn.classList.remove('bg-red-100', 'text-red-700', 'border-red-400');
        if (micStatus) micStatus.textContent = "Voice Input";
        if (state !== 'listening' && banner) {
          setTimeout(() => banner.classList.add('hidden'), 2500);
        }
      }
    },
    onTranscript: (text, isFinal) => {
      if (transcriptEl) transcriptEl.textContent = `"${text}"`;
      if (inputEl) inputEl.value = text;
    },
    onFinish: (finalText) => {
      if (inputEl) inputEl.value = finalText;
      window.DAIC.showToast(`Recognized: "${finalText}"`);
      executeAsk(finalText);
    }
  });
}

function stopVoiceInput() {
  window.DAIC.stopVoiceInput();
  const banner = document.getElementById('voice-listening-banner');
  if (banner) banner.classList.add('hidden');
  const btn = document.getElementById('voice-input-btn');
  const micStatus = document.getElementById('mic-status-text');
  if (btn) btn.classList.remove('bg-red-100', 'text-red-700', 'border-red-400');
  if (micStatus) micStatus.textContent = "Voice Input";
}
