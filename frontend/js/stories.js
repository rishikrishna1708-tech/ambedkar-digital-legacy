/**
 * DAIC Archive - Heritage Stories Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  loadStoriesList();
});

async function loadStoriesList() {
  const grid = document.getElementById('stories-grid');
  if (!grid) return;

  try {
    const data = await api.getStories();
    const stories = data.stories || [];

    grid.innerHTML = stories.map(s => `
      <div class="archival-card p-5 rounded-lg flex flex-col justify-between text-xs space-y-4">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FAF8F1] text-[#8C5B08] border border-[#EAD293]">
              ${s.timeline_year}
            </span>
            <span class="badge-verified text-[10px] px-1.5 py-0.5 rounded font-bold">
              Archival Anchored
            </span>
          </div>

          <h3 class="font-heading-cinzel font-bold text-sm text-[#141F39] leading-snug">
            ${s.title}
          </h3>

          <p class="text-gray-600 mt-2 line-clamp-3 leading-relaxed">
            ${s.excerpt}
          </p>
        </div>

        <div class="pt-3 border-t border-gray-100 flex items-center justify-between">
          <button onclick="readStory('${s.slug}')" class="px-3 py-1.5 bg-[#141F39] text-[#D7A940] rounded font-semibold text-[11px] hover:bg-[#202E4E] transition-colors flex items-center space-x-1 border border-[#D7A940]">
            <span>Read Story</span>
            <span>→</span>
          </button>
          <a href="/ask?q=Tell%20me%20about%20${encodeURIComponent(s.title)}" class="text-[#B88B28] font-bold text-[11px] hover:underline">
            Ask Assistant
          </a>
        </div>
      </div>
    `).join('');

    // Pre-open the first story
    if (stories.length > 0) {
      readStory(stories[0].slug);
    }
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-xs text-red-600">Failed to load heritage stories.</div>`;
  }
}

async function readStory(slug) {
  const reader = document.getElementById('story-reader');
  if (!reader) return;

  reader.classList.remove('hidden');
  reader.innerHTML = `<div class="py-8 text-center text-xs text-gray-500">Loading story chapters and primary citations...</div>`;

  try {
    const s = await api.getStory(slug);
    const chapters = s.chapters || [];
    const sourceDocs = s.source_documents || [];

    reader.innerHTML = `
      <div class="pb-4 border-b border-gray-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <span class="text-[10px] font-bold text-[#8C5B08] uppercase tracking-wider bg-[#FFF6E5] px-2 py-0.5 rounded border border-[#F5D399]">
            ${s.timeline_year} Heritage Narrative
          </span>
          <h2 class="font-heading-cinzel font-bold text-xl text-[#141F39] mt-1">${s.title}</h2>
          <p class="text-xs text-gray-600 mt-0.5">${s.subtitle || ''}</p>
        </div>

        <button onclick="DAIC.speakText('${(s.title + '. ' + chapters.map(c => c.heading + '. ' + c.text).join(' ')).replace(/'/g, "\\'")}')" class="px-3 py-1.5 bg-[#FAF8F1] hover:bg-[#F3EEDB] text-[#141F39] text-xs font-semibold rounded border border-gray-300 flex items-center space-x-1.5 shrink-0">
          <svg class="w-4 h-4 text-[#D7A940]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
          <span>Listen to Story</span>
        </button>
      </div>

      <!-- Narrative Chapters -->
      <div class="space-y-6 text-sm text-gray-800 leading-relaxed font-serif-archival">
        ${chapters.map((c, i) => `
          <div class="space-y-2">
            <h4 class="font-heading-cinzel font-bold text-base text-[#141F39] not-italic">${i + 1}. ${c.heading}</h4>
            <p class="text-base text-gray-800 italic leading-relaxed pl-2 border-l-2 border-[#D7A940]">${c.text}</p>
            <div class="text-[11px] font-sans not-italic text-gray-500 flex items-center space-x-1">
              <span class="font-semibold text-[#8C5B08]">Source Citation:</span>
              <span>${c.citation}</span>
            </div>
          </div>
        `).join('')}
      </div>

      <!-- Verified Sources Connection Box -->
      <div class="p-4 bg-[#FAF8F1] rounded-lg border border-[#E8E2D2] space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="font-heading-cinzel font-bold text-xs uppercase text-[#141F39] tracking-wider">
            Connected Archival Sources (${sourceDocs.length})
          </h4>
          <span class="text-[10px] text-gray-500">Every narrative chapter is verifiable in the archive</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          ${sourceDocs.map(doc => `
            <div class="p-3 bg-white rounded border border-gray-200 flex items-center justify-between">
              <div>
                <div class="font-bold text-xs text-[#141F39]">${doc.title}</div>
                <div class="text-[10px] text-gray-500">${doc.collection} • ${doc.year}</div>
              </div>
              <button onclick="DAIC.openOriginalDocument('${doc.id}')" class="px-2.5 py-1 bg-[#141F39] text-[#D7A940] rounded text-[10px] font-bold hover:bg-[#202E4E] transition-colors shrink-0 ml-2">
                Open Original
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    // Smooth scroll down to reader
    reader.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {
    reader.innerHTML = `<div class="p-6 text-center text-red-600 text-xs">Failed to load story details.</div>`;
  }
}
