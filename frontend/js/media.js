/**
 * Ambedkar Digital Legacy - Audio-Visual Media Controller
 * Renders structured archival media cards with responsive layout (3 per row desktop, 
 * 2 tablet, 1 mobile) and synchronized multi-lingual speech narration.
 */

let allMediaItems = [];
let currentMedia = null;
let currentSpeed = 1.0;

document.addEventListener('DOMContentLoaded', () => {
  loadMediaItems();

  // Listen for speech synthesis state changes
  window.addEventListener('daic:speechStateChanged', (e) => {
    updateMediaControlsUI(e.detail.state);
  });
});

async function loadMediaItems(type = 'All') {
  const grid = document.getElementById('media-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="col-span-full py-16 text-center text-gray-500 text-xs">
      <div class="w-8 h-8 mx-auto mb-2 border-2 border-[#D7A940] border-t-transparent rounded-full animate-spin"></div>
      <span>Loading archival media assets...</span>
    </div>
  `;

  try {
    const data = await api.getMedia(type);
    allMediaItems = data.media || [];
    renderMediaGrid(allMediaItems);
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-xs text-red-600">Failed to load media records.</div>`;
  }
}

function filterMedia(type) {
  document.querySelectorAll('.media-tab').forEach(tab => {
    if (tab.dataset.type === type) {
      tab.className = 'media-tab px-3 py-1.5 rounded font-semibold bg-[#D7A940] text-[#141F39]';
    } else {
      tab.className = 'media-tab px-3 py-1.5 rounded font-medium text-gray-300 hover:text-white bg-gray-800';
    }
  });
  loadMediaItems(type);
}

function renderMediaGrid(items) {
  const grid = document.getElementById('media-grid');
  if (!grid) return;

  if (items.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-gray-500 text-xs bg-white rounded border border-gray-200">
        No media assets found for this category.
      </div>
    `;
    return;
  }

  // Card Structure: TYPE -> TITLE -> DATE -> COLLECTION -> DESCRIPTION -> SOURCE -> ACTION
  grid.innerHTML = items.map(m => `
    <div class="archival-card rounded-lg p-5 flex flex-col justify-between text-xs space-y-4">
      <div class="space-y-3">
        <!-- 1. TYPE & DURATION -->
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FAF8F1] text-[#141F39] uppercase border border-gray-200 tracking-wider">
            ${m.type}
          </span>
          <span class="text-[10px] text-gray-500 font-mono">${m.duration || 'Archival Asset'}</span>
        </div>

        <!-- 2. TITLE -->
        <h3 class="font-heading-cinzel font-bold text-base text-[#141F39] leading-snug">
          ${m.title}
        </h3>

        <!-- 3. DATE -->
        <div class="text-[11px] font-semibold text-[#8C5B08]">
          ${m.date || 'Historical Period'}
        </div>

        <!-- 4. COLLECTION -->
        <div class="text-[11px] text-gray-600">
          <span class="font-medium text-gray-500">Collection:</span> ${m.collection}
        </div>

        <!-- 5. DESCRIPTION -->
        <p class="text-gray-700 leading-relaxed bg-[#FAF8F1] p-3 rounded border border-gray-100 font-normal">
          ${m.description}
        </p>

        <!-- 6. SOURCE -->
        <div class="text-[11px] text-gray-500 italic">
          <span class="font-semibold text-gray-600 not-italic">Source:</span> ${m.source_institution || 'All India Radio & Parliamentary Archives'}
        </div>
      </div>

      <!-- 7. ACTION -->
      <div class="pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
        <button onclick="selectAndPlayMedia('${m.id}')" class="px-3.5 py-1.5 bg-[#141F39] text-[#D7A940] rounded font-semibold text-xs hover:bg-[#202E4E] transition-colors flex items-center space-x-1.5 border border-[#D7A940]">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <span>${m.type === 'photo' ? 'View Details' : 'Listen'}</span>
        </button>

        <button onclick="DAIC.addToResearch('${m.title.replace(/'/g, "\\'")}', '${(m.description || '').replace(/'/g, "\\'")}', null, null, null, '${m.collection.replace(/'/g, "\\'")}')" class="text-[#B88B28] hover:underline font-bold text-xs">
          + Add to Research
        </button>
      </div>
    </div>
  `).join('');
}

function selectAndPlayMedia(id) {
  const m = allMediaItems.find(item => item.id === id);
  if (!m) return;

  currentMedia = m;
  const title = document.getElementById('current-player-title');
  const desc = document.getElementById('current-player-desc');

  if (title) title.textContent = m.title;
  if (desc) desc.textContent = `${m.collection} • ${m.date}`;

  // Start speech narration
  const narration = m.audio_narration_text || m.description;
  window.DAIC.speakText(narration, currentSpeed);
}

function togglePlayer() {
  if (!currentMedia) {
    if (allMediaItems.length > 0) {
      selectAndPlayMedia(allMediaItems[0].id);
    }
    return;
  }

  if (window.DAIC.isSpeaking && !window.DAIC.isPaused) {
    window.DAIC.pauseSpeaking();
  } else if (window.DAIC.isPaused) {
    window.DAIC.resumeSpeaking();
  } else {
    const narration = currentMedia.audio_narration_text || currentMedia.description;
    window.DAIC.speakText(narration, currentSpeed);
  }
}

function stopPlayer() {
  window.DAIC.stopSpeaking();
}

function changeSpeed(val) {
  currentSpeed = parseFloat(val);
  window.DAIC.setSpeechRate(currentSpeed);
}

function updateMediaControlsUI(state) {
  const playBtn = document.getElementById('media-play-btn');
  const pauseBtn = document.getElementById('media-pause-btn');

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
