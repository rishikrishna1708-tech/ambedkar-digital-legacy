/**
 * Ambedkar Digital Legacy - Visitor Kiosk Controller
 * Handles large-format touch interactions, touch language selection,
 * and localized voice input without hardcoded language codes.
 */

document.addEventListener('DOMContentLoaded', () => {
  const cur = (window.DAIC && window.DAIC.currentLanguage) || localStorage.getItem('daic_lang') || 'en';
  document.querySelectorAll('.k-lang').forEach(btn => {
    if (btn.dataset.kLang === cur) {
      btn.className = 'k-lang px-3 py-1.5 text-xs rounded font-bold bg-[#D7A940] text-[#141F39]';
    } else {
      btn.className = 'k-lang px-3 py-1.5 text-xs rounded font-medium text-gray-300 hover:text-white';
    }
  });
});

function setKioskLanguage(lang) {
  if (window.DAIC && typeof window.DAIC.setLanguage === 'function') {
    window.DAIC.setLanguage(lang);
  }
  document.querySelectorAll('.k-lang').forEach(btn => {
    if (btn.dataset.kLang === lang) {
      btn.className = 'k-lang px-3 py-1.5 text-xs rounded font-bold bg-[#D7A940] text-[#141F39]';
    } else {
      btn.className = 'k-lang px-3 py-1.5 text-xs rounded font-medium text-gray-300 hover:text-white';
    }
  });
}

function kioskAskQuestion(q) {
  window.location.href = `/ask?q=${encodeURIComponent(q)}`;
}

function openKioskAskModal() {
  const modal = document.getElementById('kiosk-ask-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeKioskAskModal() {
  const modal = document.getElementById('kiosk-ask-modal');
  if (modal) modal.classList.add('hidden');
  window.DAIC.stopVoiceInput();
}

function submitKioskQuery() {
  const input = document.getElementById('kiosk-input');
  if (input && input.value.trim()) {
    window.location.href = `/ask?q=${encodeURIComponent(input.value.trim())}`;
  }
}

function startKioskVoice() {
  const statusBox = document.getElementById('kiosk-voice-status');
  const statusText = document.getElementById('kiosk-voice-text');
  const micBtn = document.getElementById('kiosk-mic-btn');
  const micBtnText = document.getElementById('kiosk-mic-btn-text');
  const input = document.getElementById('kiosk-input');

  const currentLang = window.DAIC.currentLanguage || 'en';
  const langInfo = window.DAIC.VOICE_LANG_MAP[currentLang] || { native: 'English' };

  if (window.DAIC.recognitionState === 'listening') {
    window.DAIC.stopVoiceInput();
    if (statusBox) statusBox.classList.add('hidden');
    if (micBtnText) micBtnText.textContent = "Touch to Speak";
    if (micBtn) micBtn.classList.remove('bg-red-700');
    return;
  }

  if (statusBox) statusBox.classList.remove('hidden');
  if (statusText) statusText.textContent = `Listening in ${langInfo.native}... Speak your research inquiry`;
  if (micBtnText) micBtnText.textContent = "■ Stop Listening";
  if (micBtn) micBtn.classList.add('bg-red-700');

  const started = window.DAIC.startVoiceInput({
    onStateChange: (state) => {
      if (state !== 'listening') {
        if (micBtnText) micBtnText.textContent = "Touch to Speak";
        if (micBtn) micBtn.classList.remove('bg-red-700');
        if (state === 'error') {
          if (statusText) statusText.textContent = "Voice input unavailable or timed out.";
        }
      }
    },
    onTranscript: (text) => {
      if (input) input.value = text;
      if (statusText) statusText.textContent = `"${text}"`;
    },
    onFinish: (finalText) => {
      if (input) input.value = finalText;
      if (statusText) statusText.textContent = `Recognized: "${finalText}"`;
      setTimeout(() => {
        window.location.href = `/ask?q=${encodeURIComponent(finalText)}`;
      }, 700);
    }
  });

  if (!started) {
    if (statusBox) statusBox.classList.add('hidden');
    if (micBtnText) micBtnText.textContent = "Touch to Speak";
    if (micBtn) micBtn.classList.remove('bg-red-700');
  }
}
