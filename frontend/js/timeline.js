/**
 * DAIC Archive - Timeline Controller
 */

let allTimelineEvents = [];
let currentCategory = 'All';

document.addEventListener('DOMContentLoaded', () => {
  loadTimelineEvents();
});

async function loadTimelineEvents(category = 'All') {
  currentCategory = category;
  const container = document.getElementById('timeline-container');
  if (!container) return;

  try {
    const data = await api.getTimeline(category);
    allTimelineEvents = data.events || [];
    renderTimeline(allTimelineEvents);
  } catch (e) {
    container.innerHTML = `<div class="p-6 text-center text-xs text-red-600">Failed to load timeline events.</div>`;
  }
}

function filterTimeline(cat) {
  document.querySelectorAll('.tl-filter-btn').forEach(btn => {
    if (btn.dataset.cat === cat) {
      btn.className = 'tl-filter-btn px-2.5 py-1 rounded text-xs font-semibold bg-[#D7A940] text-[#141F39]';
    } else {
      btn.className = 'tl-filter-btn px-2.5 py-1 rounded text-xs font-medium text-gray-300 hover:text-white bg-gray-800';
    }
  });
  loadTimelineEvents(cat);
}

function renderTimeline(events) {
  const container = document.getElementById('timeline-container');
  if (!container) return;

  if (events.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center text-xs text-gray-500 bg-white rounded border border-gray-200 ml-6">
        No historical milestones found for this category.
      </div>
    `;
    return;
  }

  container.innerHTML = events.map(evt => {
    const docs = evt.related_documents || [];
    const people = evt.related_people || [];

    return `
      <div class="relative pl-6 sm:pl-8 group">
        <!-- Gold Node on Left Track -->
        <div class="absolute -left-[11px] top-1.5 w-5 h-5 rounded-full bg-[#141F39] border-2 border-[#D7A940] group-hover:scale-125 transition-transform flex items-center justify-center shadow">
          <div class="w-1.5 h-1.5 rounded-full bg-[#D7A940]"></div>
        </div>

        <!-- Date indicator (Desktop left tag simulation) -->
        <div class="md:absolute md:-left-28 md:top-1 text-xs font-bold text-[#8C5B08] uppercase tracking-wider mb-1 md:mb-0">
          ${evt.year}
        </div>

        <!-- Event Archival Card -->
        <div class="archival-card p-5 rounded-lg bg-white border border-[#E8E2D2] text-xs space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FAF8F1] text-[#141F39] border border-gray-200">
              ${evt.category}
            </span>
            <span class="text-[11px] text-gray-500 font-medium">${evt.date_str}</span>
          </div>

          <h3 class="font-heading-cinzel font-bold text-base text-[#141F39]">
            ${evt.title}
          </h3>

          ${evt.quote ? `
            <blockquote class="border-l-2 border-[#D7A940] pl-3 py-1 font-serif-archival italic text-gray-800 bg-[#FAF8F1] rounded text-xs">
              "${evt.quote}"
            </blockquote>
          ` : ''}

          <p class="text-gray-700 leading-relaxed text-xs">
            ${evt.description}
          </p>

          <!-- Linked Archival Entities -->
          <div class="pt-2 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center space-x-2">
              ${people.map(p => `
                <span class="text-[10px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                  ${p}
                </span>
              `).join('')}
            </div>

            <div class="flex items-center space-x-2">
              <button onclick="DAIC.speakText('${evt.description.replace(/'/g, "\\'")}')" class="text-[11px] text-gray-500 hover:text-[#141F39] flex items-center space-x-1" title="Listen to Narration">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
                <span>Listen</span>
              </button>

              ${docs.length > 0 ? `
                <button onclick="DAIC.openOriginalDocument('${docs[0]}')" class="px-2.5 py-1 bg-[#141F39] text-[#D7A940] rounded text-[11px] font-semibold hover:bg-[#202E4E] transition-colors flex items-center space-x-1">
                  <span>View Primary Source</span>
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}
