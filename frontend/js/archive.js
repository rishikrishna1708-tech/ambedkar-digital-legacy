/**
 * Ambedkar Digital Legacy - Catalogue Browser Controller
 * Manages institutional archive document retrieval with multi-faceted filtering
 * (Collection, Document Type, Year, Language, Search) and provenance cards.
 */

document.addEventListener('DOMContentLoaded', () => {
  initArchivePage();
});

function initArchivePage() {
  const searchInput = document.getElementById('search-input');
  const typeFilter = document.getElementById('type-filter');
  const collectionFilter = document.getElementById('collection-filter');
  const yearFilter = document.getElementById('year-filter');
  const languageFilter = document.getElementById('language-filter');
  const applyBtn = document.getElementById('apply-filter-btn');
  const resetBtn = document.getElementById('reset-filter-btn');

  // Handle URL query parameters if present
  const params = new URLSearchParams(window.location.search);
  if (params.get('q') && searchInput) searchInput.value = params.get('q');
  if (params.get('type') && typeFilter) typeFilter.value = params.get('type');
  if (params.get('collection') && collectionFilter) collectionFilter.value = params.get('collection');

  loadDocuments();

  if (applyBtn) {
    applyBtn.addEventListener('click', () => loadDocuments());
  }
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (typeFilter) typeFilter.value = 'All';
      if (collectionFilter) collectionFilter.value = 'All';
      if (yearFilter) yearFilter.value = 'All';
      if (languageFilter) languageFilter.value = 'All';
      const verifFilter = document.getElementById('verification-filter');
      const provFilter = document.getElementById('provenance-filter');
      if (verifFilter) verifFilter.value = 'All';
      if (provFilter) provFilter.value = 'All';
      loadDocuments();
    });
  }

  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') loadDocuments();
    });
  }
}

async function loadDocuments() {
  const grid = document.getElementById('archive-grid');
  const countBadge = document.getElementById('results-count-badge');
  if (!grid) return;

  grid.innerHTML = `
    <div class="col-span-full py-16 text-center text-gray-500 text-xs">
      <div class="w-8 h-8 mx-auto mb-2 border-2 border-[#D7A940] border-t-transparent rounded-full animate-spin"></div>
      <span>Querying authenticated archival repository records...</span>
    </div>
  `;

  const q = document.getElementById('search-input')?.value.trim();
  const type = document.getElementById('type-filter')?.value;
  const collection = document.getElementById('collection-filter')?.value;
  const yearRange = document.getElementById('year-filter')?.value;
  const lang = document.getElementById('language-filter')?.value;
  const verificationStatus = document.getElementById('verification-filter')?.value;
  const provenanceType = document.getElementById('provenance-filter')?.value;

  try {
    const data = await api.getArchive({ q, type, collection, verification_status: verificationStatus, provenance_type: provenanceType });
    let docs = data.documents || [];

    // Client-side refinement for Year and Language filters if selected
    if (yearRange && yearRange !== 'All') {
      const [start, end] = yearRange.split('-').map(Number);
      docs = docs.filter(d => {
        const y = d.year || parseInt(d.date_str) || 0;
        return y >= start && y <= end;
      });
    }

    if (lang && lang !== 'All') {
      docs = docs.filter(d => (d.language || 'en').toLowerCase().includes(lang.toLowerCase()));
    }

    if (countBadge) {
      countBadge.textContent = `${docs.length} Archival Record${docs.length === 1 ? '' : 's'}`;
    }

    if (docs.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-16 text-center text-gray-500 text-xs bg-white rounded-lg border border-gray-200 p-8">
          <svg class="w-12 h-12 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <p class="font-bold text-gray-700">No archival records found matching criteria</p>
          <p class="text-gray-500 mt-1">Try clearing filters or broadening search parameters.</p>
        </div>
      `;
      return;
    }

    // Cards display: Title, Date, Collection, Document type, Pages, Verification
    grid.innerHTML = docs.map(doc => {
      const year = doc.date_str || doc.year || 'Historical';
      const pages = doc.page_count || 1;
      
      let badgeClass = "bg-emerald-100 text-emerald-800 border border-emerald-300";
      let badgeText = "✓ VERIFIED SOURCE";

      if (doc.verification_status === "UNVERIFIED (NEW INGESTION)" || (doc.provenance_type === "USER-UPLOADED DATA" && doc.verification_status !== "VERIFIED SOURCE")) {
        badgeClass = "bg-amber-100 text-amber-800 border border-amber-300";
        badgeText = "⏳ USER-UPLOADED DATA";
      } else if (doc.provenance_type === "DEMO DATA") {
        badgeClass = "bg-[#FFF6E5] text-[#8C5B08] border border-[#F5D399]";
        badgeText = "DEMO DATA";
      }

      return `
        <div class="archival-card rounded-lg p-5 flex flex-col justify-between text-xs space-y-4">
          <div class="space-y-3">
            <!-- Header Badges: Document Type & Verification -->
            <div class="flex items-center justify-between gap-1">
              <div class="flex items-center space-x-1.5">
                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-[#141F39] border border-gray-200 uppercase tracking-wider">
                  ${doc.type}
                </span>
                <span class="text-[10px] font-mono font-bold text-gray-500">
                  ${doc.id}
                </span>
              </div>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded ${badgeClass}">
                ${badgeText}
              </span>
            </div>

            <!-- Title -->
            <h3 class="font-heading-cinzel font-bold text-sm text-[#141F39] leading-snug line-clamp-2">
              ${doc.title}
            </h3>

            <!-- Metadata Details: Collection, Date, Pages -->
            <div class="space-y-1 text-gray-600 text-[11px] pt-1 border-t border-gray-100">
              <div><strong class="text-gray-500">Collection:</strong> ${doc.collection}</div>
              <div><strong class="text-gray-500">Author:</strong> ${doc.author}</div>
              <div class="flex items-center space-x-3 text-gray-500 pt-0.5">
                <span><strong>Date:</strong> ${year}</span>
                <span>•</span>
                <span><strong>Pages:</strong> ${pages}</span>
                <span>•</span>
                <span><strong>Language:</strong> ${(doc.language || 'English').toUpperCase()}</span>
              </div>
            </div>

            <!-- Summary -->
            <p class="text-gray-700 line-clamp-3 leading-relaxed bg-[#FAF8F1] p-2.5 rounded border border-gray-100">
              ${doc.summary || 'Archival document cataloged under institutional digital heritage preservation.'}
            </p>
          </div>

          <!-- Bottom Action Buttons -->
          <div class="pt-3 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2">
            <button onclick="DAIC.openOriginalDocument('${doc.id}')" class="px-2.5 py-1.5 bg-[#141F39] hover:bg-[#202E4E] text-[#D7A940] rounded font-semibold text-[11px] transition-colors flex items-center space-x-1 border border-[#D7A940]">
              <span>Read Original</span>
            </button>

            <a href="/ask?q=Tell%20me%20about%20${encodeURIComponent(doc.title)}" class="px-2.5 py-1.5 bg-gray-100 hover:bg-gray-200 text-[#141F39] rounded font-semibold text-[11px] transition-colors border border-gray-300">
              Ask AI Assistant
            </a>

            <button onclick="DAIC.addToResearch('${doc.title.replace(/'/g, "\\'")}', '${(doc.summary || '').replace(/'/g, "\\'")}', 1, '${doc.id}', null, '${doc.collection.replace(/'/g, "\\'")}')" class="text-[#B88B28] hover:underline font-bold text-[11px]">
              + Research
            </button>
          </div>
        </div>
      `;
    }).join('');

  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-red-600 text-xs">Failed to load archival records.</div>`;
  }
}
