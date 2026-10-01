/**
 * Ambedkar Digital Legacy - Global Application Controller
 * Handles persistent institutional header, research notebook, speech synthesis & recognition,
 * institutional about modal, and shared UI controllers.
 */

window.DAIC = {
  currentLanguage: localStorage.getItem('daic_lang') || 'en',
  speechRate: 1.0,
  isSpeaking: false,
  isPaused: false,
  currentUtterance: null,
  activeRecognition: null,
  recognitionState: 'idle', // 'idle' | 'listening' | 'processing' | 'completed' | 'error'
  recognitionCallback: null,

  VOICE_LANG_MAP: {
    en: { bcp47: 'en-IN', name: 'English (India)', native: 'English', label: 'EN' },
    hi: { bcp47: 'hi-IN', name: 'Hindi', native: 'हिन्दी', label: 'हिन्दी' },
    mr: { bcp47: 'mr-IN', name: 'Marathi', native: 'मराठी', label: 'मराठी' },
    kn: { bcp47: 'kn-IN', name: 'Kannada', native: 'ಕನ್ನಡ', label: 'ಕನ್ನಡ' },
    ta: { bcp47: 'ta-IN', name: 'Tamil', native: 'தமிழ்', label: 'தமிழ்' }
  },

  t(key, lang = null) {
    const l = lang || this.currentLanguage || 'en';
    const dict = window.DAIC_I18N;
    if (dict && dict[key]) {
      return dict[key][l] || dict[key]['en'] || key;
    }
    return key;
  },

  applyTranslations(lang = null) {
    const l = lang || this.currentLanguage || 'en';
    document.documentElement.lang = l;

    // Apply text translations for elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      const text = this.t(key, l);
      if (text) {
        const targetSpan = el.querySelector('.i18n-target') || (el.children.length > 0 ? el.querySelector('span:not([class*="icon"]):not([class*="badge"])') : null);
        if (targetSpan && !el.classList.contains('i18n-direct')) {
          targetSpan.textContent = text;
        } else {
          el.textContent = text;
        }
      }
    });

    // Apply placeholder translations
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.dataset.i18nPlaceholder;
      const text = this.t(key, l);
      if (text) el.placeholder = text;
    });

    // Apply title translations
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.dataset.i18nTitle;
      const text = this.t(key, l);
      if (text) el.title = text;
    });

    // Apply aria-label translations
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.dataset.i18nAria;
      const text = this.t(key, l);
      if (text) el.setAttribute('aria-label', text);
    });
  },

  init() {
    this.renderHeader();
    this.renderFooter();
    this.initResearchDrawer();
    this.initAboutModal();
    this.initDocumentModal();
    this.checkVoiceSupport();
    this.applyTranslations(this.currentLanguage);
  },

  setLanguage(lang) {
    if (!this.VOICE_LANG_MAP[lang]) lang = 'en';
    this.currentLanguage = lang;
    localStorage.setItem('daic_lang', lang);

    // Re-render persistent header & footer in new language
    this.renderHeader();
    this.renderFooter();

    // Apply in-page translations across active DOM
    this.applyTranslations(lang);

    const langInfo = this.VOICE_LANG_MAP[lang];
    const toastMsg = this.t('toast_lang_changed', lang) || `Language set to ${langInfo.native} (${langInfo.bcp47})`;
    this.showToast(toastMsg);

    // Safely update speech recognition if currently active
    if (this.recognitionState === 'listening' && this.activeRecognition) {
      try {
        this.activeRecognition.abort();
      } catch (e) {}
      // Restart listening with the new language
      setTimeout(() => {
        if (this.recognitionCallback) {
          this.startListening(this.recognitionCallback);
        }
      }, 250);
    }

    // Stop speaking if speech was in progress
    if (this.isSpeaking) {
      this.stopSpeaking();
    }

    // Dispatch global event for page listeners
    window.dispatchEvent(new CustomEvent('daic:languageChanged', { detail: { lang, langInfo } }));
  },

  toggleMobileNav() {
    const menu = document.getElementById('mobile-nav-menu');
    if (menu) {
      menu.classList.toggle('hidden');
    }
  },

  renderHeader() {
    const headerContainer = document.getElementById('global-header');
    if (!headerContainer) return;

    const currentPath = window.location.pathname;
    const navItems = [
      { key: 'nav_home', name: this.t('nav_home'), href: '/' },
      { key: 'nav_ask', name: this.t('nav_ask'), href: '/ask' },
      { key: 'nav_timeline', name: this.t('nav_timeline'), href: '/timeline-view' },
      { key: 'nav_archive', name: this.t('nav_archive'), href: '/archive-view' },
      { key: 'nav_manuscripts', name: this.t('nav_manuscripts'), href: '/manuscripts' },
      { key: 'nav_media', name: this.t('nav_media'), href: '/media-view' },
      { key: 'nav_stories', name: this.t('nav_stories'), href: '/stories-view' },
      { key: 'nav_knowledge', name: this.t('nav_knowledge'), href: '/knowledge-view' }
    ];

    // Desktop nav items in 2 clean rows of 4 items to ensure zero collision at all resolutions
    const row1 = navItems.slice(0, 4);
    const row2 = navItems.slice(4, 8);

    const renderLink = (item) => {
      const isActive = currentPath === item.href || (item.href !== '/' && currentPath.includes(item.href.replace('-view', '')));
      return `
        <a href="${item.href}" class="px-2.5 py-1 text-xs font-semibold whitespace-nowrap rounded transition-colors ${
          isActive 
            ? 'text-[#D7A940] bg-[#1B294B] font-bold border-b border-[#D7A940]' 
            : 'text-gray-200 hover:text-white hover:bg-[#1B294B]/60'
        }">${item.name}</a>
      `;
    };

    const mobileNavLinksHtml = navItems.map(item => {
      const isActive = currentPath === item.href || (item.href !== '/' && currentPath.includes(item.href.replace('-view', '')));
      return `
        <a href="${item.href}" class="block px-3 py-2 text-sm font-medium transition-colors rounded ${
          isActive ? 'bg-[#D7A940] text-[#141F39] font-bold' : 'text-gray-200 hover:bg-[#1B294B]'
        }">${item.name}</a>
      `;
    }).join('');

    const langHtml = Object.entries(this.VOICE_LANG_MAP).map(([code, info]) => `
      <button 
        onclick="DAIC.setLanguage('${code}')" 
        data-lang="${code}" 
        class="lang-btn px-2 py-0.5 text-[11px] rounded transition-colors ${
          this.currentLanguage === code 
            ? 'bg-[#D7A940] text-[#141F39] font-bold' 
            : 'text-gray-300 hover:text-white'
        }"
        title="${info.name}">
        ${info.label}
      </button>
    `).join('');

    headerContainer.innerHTML = `
      <header class="adl-header shadow-md">
        <!-- Top Institutional Utility Bar -->
        <div class="adl-topbar py-1.5 px-4 sm:px-6">
          <div class="global-container flex justify-between items-center text-[11px] text-gray-400">
            <!-- Left: Institutional Identity -->
            <div class="flex items-center space-x-2 truncate">
              <span class="text-gray-300 font-semibold tracking-wide">${this.t('institution_label')}</span>
              <span class="text-[#D7A940]">•</span>
              <span class="text-gray-300">${this.t('institution_center')}</span>
            </div>

            <!-- Right: Languages & Administrative Tools -->
            <div class="flex items-center space-x-3 shrink-0">
              <!-- Multilingual Selector -->
              <div class="hidden sm:flex items-center bg-[#0D1527] rounded p-0.5 border border-gray-700">
                ${langHtml}
              </div>

              <!-- Research Notebook Drawer Toggle -->
              <button onclick="DAIC.openResearchDrawer()" title="Open Research Notebook" class="p-1.5 text-gray-300 hover:text-[#D7A940] hover:bg-[#0D1527] rounded transition-colors relative flex items-center space-x-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                </svg>
                <span class="hidden md:inline text-[11px]">${this.t('btn_research_notes')}</span>
                <span id="research-count-badge" class="hidden absolute -top-1 -right-1 bg-[#D7A940] text-[#141F39] text-[9px] font-bold rounded-full w-3.5 h-3.5 flex items-center justify-center">0</span>
              </button>

              <!-- Discreet Archivist Admin Portal -->
              <a href="/admin" title="Archivist Management Dashboard" class="p-1.5 text-gray-400 hover:text-white transition-colors flex items-center space-x-1" aria-label="Archivist Dashboard">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
              </a>
            </div>
          </div>
        </div>

        <!-- Main Header Bar -->
        <div class="global-container py-3">
          <div class="flex items-center justify-between gap-4">
            
            <!-- LEFT: Institution & Product Branding -->
            <a href="/" class="flex items-center space-x-3 text-white group shrink-0">
              <div class="w-10 h-10 rounded-full border-2 border-[#D7A940] bg-[#0D1527] flex items-center justify-center p-1 shadow-inner shrink-0">
                <svg class="w-6 h-6 text-[#D7A940]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10"/>
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M12 2v7M12 15v7M2 12h7M15 12h7M4.93 4.93l4.95 4.95M14.12 14.12l4.95 4.95M4.93 19.07l4.95-4.95M14.12 9.88l4.95-4.95"/>
                </svg>
              </div>
              <div class="flex flex-col min-w-0">
                <div class="font-heading-cinzel tracking-wider text-base sm:text-lg font-bold text-white leading-tight">
                  ${this.t('app_title')}
                </div>
                <div class="text-[11px] text-[#D7A940] font-medium tracking-normal leading-tight mt-0.5">
                  ${this.t('app_subtitle')}
                </div>
              </div>
            </a>

            <!-- CENTER: Desktop Navigation in 2 Structured Rows (Never Collides) -->
            <nav class="hidden lg:flex flex-col items-center justify-center space-y-1 shrink-0 px-2" aria-label="Main Navigation">
              <div class="flex items-center space-x-1">
                ${row1.map(renderLink).join('')}
              </div>
              <div class="flex items-center space-x-1">
                ${row2.map(renderLink).join('')}
              </div>
            </nav>

            <!-- RIGHT: Visitor Mode & About Platform Buttons -->
            <div class="flex items-center space-x-2 sm:space-x-2.5 shrink-0">
              <!-- Visitor Mode Button (Institutional Kiosk) -->
              <a href="/visitor" class="flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-bold bg-[#D7A940] hover:bg-[#C29532] text-[#141F39] transition-all shadow-sm whitespace-nowrap">
                <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
                <span>${this.t('btn_visitor_mode')}</span>
              </a>

              <!-- About the Platform Modal Trigger -->
              <button onclick="DAIC.openAboutModal()" class="flex items-center space-x-1 px-3 py-1.5 rounded text-xs font-semibold bg-[#1B294B] hover:bg-[#253966] text-[#D7A940] border border-[#D7A940]/50 transition-colors whitespace-nowrap" aria-label="About the Platform">
                <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span>${this.t('btn_about')}</span>
              </button>

              <!-- Hamburger Toggle Button for Mobile / Tablet -->
              <button onclick="DAIC.toggleMobileNav()" title="Toggle Navigation Menu" class="lg:hidden p-2 text-gray-300 hover:text-white rounded focus:outline-none" aria-label="Open Navigation">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"/>
                </svg>
              </button>
            </div>

          </div>
        </div>

        <!-- Collapsible Mobile / Tablet Navigation Menu -->
        <div id="mobile-nav-menu" class="hidden lg:hidden bg-[#0D1527] border-t border-gray-800 px-4 py-3 space-y-1">
          ${mobileNavLinksHtml}
          <div class="pt-3 mt-2 border-t border-gray-800 flex items-center justify-between">
            <span class="text-xs text-gray-400">${this.t('filter_language') || 'Language'}:</span>
            <div class="flex items-center space-x-1">
              ${langHtml}
            </div>
          </div>
          <div class="pt-2 flex items-center justify-between">
            <a href="/visitor" class="text-xs text-[#D7A940] font-bold">Launch ${this.t('btn_visitor_mode')} →</a>
            <button onclick="DAIC.openAboutModal()" class="text-xs text-gray-400 hover:text-white">${this.t('btn_about')} ${this.t('app_title')}</button>
          </div>
        </div>
      </header>
    `;
    this.updateResearchCount();
  },

  renderFooter() {
    const footerContainer = document.getElementById('global-footer');
    if (!footerContainer) return;

    footerContainer.innerHTML = `
      <footer class="bg-[#141F39] text-gray-300 border-t border-[#D7A940]/40 mt-16 pt-12 pb-8">
        <div class="global-container">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <!-- Brand & Context -->
            <div class="col-span-1 md:col-span-2">
              <div class="text-white font-heading-cinzel text-lg font-bold mb-1">
                ${this.t('app_title')}
              </div>
              <div class="text-xs text-[#D7A940] font-medium mb-3">
                ${this.t('app_subtitle')}
              </div>
              <p class="text-xs text-gray-400 mb-2 font-medium">
                ${this.t('institution_label')} • ${this.t('institution_center')}
              </p>
              <p class="text-xs text-gray-400 mb-4 max-w-md leading-relaxed">
                ${this.t('about_mission_desc')}
              </p>
              <div class="flex items-center space-x-2 text-[11px] text-[#D7A940] font-semibold">
                <span>${this.t('principle_preserve')}</span>
                <span>•</span>
                <span>${this.t('principle_discover')}</span>
                <span>•</span>
                <span>${this.t('principle_understand')}</span>
                <span>•</span>
                <span>${this.t('principle_verify')}</span>
                <span>•</span>
                <span>${this.t('principle_learn')}</span>
              </div>
            </div>

            <!-- Explore Collections -->
            <div>
              <h4 class="text-white text-xs font-semibold tracking-wider uppercase mb-3">${this.t('section_collections_title')}</h4>
              <ul class="text-xs space-y-2 text-gray-400">
                <li><a href="/" class="hover:text-white">${this.t('nav_home')}</a></li>
                <li><a href="/archive-view" class="hover:text-white">${this.t('nav_archive')}</a></li>
                <li><a href="/manuscripts" class="hover:text-white">${this.t('nav_manuscripts')}</a></li>
                <li><a href="/timeline-view" class="hover:text-white">${this.t('nav_timeline')}</a></li>
                <li><a href="/media-view" class="hover:text-white">${this.t('nav_media')}</a></li>
                <li><a href="/knowledge-view" class="hover:text-white">${this.t('nav_knowledge')}</a></li>
              </ul>
            </div>

            <!-- Research & Accessibility -->
            <div>
              <h4 class="text-white text-xs font-semibold tracking-wider uppercase mb-3">Research & Access</h4>
              <ul class="text-xs space-y-2 text-gray-400">
                <li><a href="/ask" class="hover:text-white text-[#D7A940]">${this.t('btn_ask_archive')}</a></li>
                <li><a href="/stories-view" class="hover:text-white">${this.t('nav_stories')}</a></li>
                <li><a href="/visitor" class="hover:text-white">${this.t('btn_visitor_mode')}</a></li>
                <li><button onclick="DAIC.openAboutModal()" class="hover:text-white text-left">${this.t('btn_about')}</button></li>
                <li><a href="/admin" class="hover:text-white">Archivist Ingestion Portal</a></li>
              </ul>
            </div>
          </div>

          <div class="border-t border-gray-800 pt-6 flex flex-col md:flex-row justify-between items-center text-xs text-gray-500 gap-3">
            <div>
              © ${this.t('app_title')} • ${this.t('institution_label')} • ${this.t('institution_center')}
            </div>
            <div class="flex space-x-3">
              <span class="px-2 py-0.5 rounded bg-gray-800 text-[#D7A940]">Strict Evidence Grounded</span>
              <span class="px-2 py-0.5 rounded bg-gray-800 text-gray-300">Zero AI Hallucination Policy</span>
            </div>
          </div>
        </div>
      </footer>
    `;
  },


  // Research Notebook Drawer
  initResearchDrawer() {
    let drawer = document.getElementById('research-drawer');
    if (!drawer) {
      drawer = document.createElement('div');
      drawer.id = 'research-drawer';
      drawer.className = 'fixed inset-0 z-50 overflow-hidden hidden';
      drawer.innerHTML = `
        <div class="drawer-overlay absolute inset-0" onclick="DAIC.closeResearchDrawer()"></div>
        <div class="absolute inset-y-0 right-0 max-w-full flex pl-10">
          <div class="w-screen max-w-md bg-white shadow-2xl flex flex-col">
            <div class="p-4 bg-[#141F39] text-white flex justify-between items-center border-b border-[#D7A940]">
              <div class="flex items-center space-x-2">
                <svg class="w-5 h-5 text-[#D7A940]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                </svg>
                <h3 class="font-heading-cinzel font-bold text-sm tracking-wide">Research Collection</h3>
              </div>
              <button onclick="DAIC.closeResearchDrawer()" class="text-gray-400 hover:text-white">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            
            <div id="research-items-list" class="flex-1 overflow-y-auto p-4 space-y-3 bg-[#F8F4E8]">
              <p class="text-xs text-gray-500 text-center py-8">Loading research notebook...</p>
            </div>

            <div class="p-4 bg-white border-t border-gray-200 flex space-x-2">
              <button onclick="DAIC.exportResearch('markdown')" class="flex-1 px-3 py-2 text-xs font-semibold bg-[#141F39] text-[#D7A940] rounded hover:bg-[#202E4E] transition-colors">
                Export Markdown
              </button>
              <button onclick="DAIC.exportResearch('json')" class="px-3 py-2 text-xs font-semibold bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors">
                Export JSON
              </button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(drawer);
    }
  },

  async openResearchDrawer() {
    const drawer = document.getElementById('research-drawer');
    if (!drawer) return;
    drawer.classList.remove('hidden');
    await this.refreshResearchItems();
  },

  closeResearchDrawer() {
    const drawer = document.getElementById('research-drawer');
    if (drawer) drawer.classList.add('hidden');
  },

  async refreshResearchItems() {
    const list = document.getElementById('research-items-list');
    if (!list) return;

    try {
      const data = await api.getResearch();
      const items = data.items || [];
      this.currentResearchItems = items;
      this.updateResearchCount(items.length);

      if (items.length === 0) {
        list.innerHTML = `
          <div class="text-center py-12 px-4">
            <svg class="w-12 h-12 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <p class="text-sm font-medium text-gray-700">No saved research citations</p>
            <p class="text-xs text-gray-500 mt-1">Click "+ Research" or "+ Add to Research" on any archival evidence card to save verified citations.</p>
          </div>
        `;
        return;
      }

      list.innerHTML = items.map(item => `
        <div class="archival-card p-3 rounded bg-white border border-[#E8E2D2] text-left">
          <div class="flex justify-between items-start mb-1">
            <h4 class="text-xs font-bold text-[#141F39] line-clamp-1">${item.title}</h4>
            <button onclick="DAIC.deleteResearchItem('${item.id}')" class="text-gray-400 hover:text-red-600 text-xs ml-2">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
          ${item.page ? `<span class="inline-block text-[10px] bg-[#FBF4E2] text-[#8C5B08] px-1.5 py-0.5 rounded font-medium mb-1">Page ${item.page}</span>` : ''}
          ${item.quote ? `<p class="text-xs text-gray-700 italic border-l-2 border-[#D7A940] pl-2 my-1 font-serif-archival">"${item.quote}"</p>` : ''}
          ${item.source_title ? `<p class="text-[10px] text-gray-500 mt-1">Source: ${item.source_title}</p>` : ''}
          <div class="text-[9px] text-gray-400 mt-2">${new Date(item.created_at).toLocaleDateString()}</div>
        </div>
      `).join('');
    } catch (e) {
      list.innerHTML = `<p class="text-xs text-red-500 py-4 text-center">Failed to load research items.</p>`;
    }
  },

  async updateResearchCount(count = null) {
    const badge = document.getElementById('research-count-badge');
    if (!badge) return;
    if (count === null) {
      try {
        const data = await api.getResearch();
        count = (data.items || []).length;
      } catch (e) {
        count = 0;
      }
    }
    if (count > 0) {
      badge.textContent = count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  },

  async addToResearch(title, quote = '', page = null, docId = null, chunkId = null, sourceTitle = '') {
    try {
      await api.saveResearch({
        collection_id: "DEFAULT_COLLECTION",
        document_id: docId,
        chunk_id: chunkId,
        title: title || 'Archival Citation',
        quote: quote,
        page: page,
        source_title: sourceTitle,
        notes: "Saved from interactive archival research session."
      });
      this.showToast("✓ Added to Research Collection");
      this.updateResearchCount();
    } catch (e) {
      this.showToast("Error saving research citation", "error");
    }
  },

  async deleteResearchItem(itemId) {
    try {
      await api.deleteResearch(itemId);
      this.showToast("Removed from research");
      await this.refreshResearchItems();
    } catch (e) {
      this.showToast("Failed to remove item", "error");
    }
  },

  exportResearch(format = 'markdown') {
    if (!this.currentResearchItems || this.currentResearchItems.length === 0) {
      this.showToast("No research items to export", "error");
      return;
    }

    let content = "";
    let mime = "text/plain";
    let filename = `ambedkar_legacy_research.${format === 'json' ? 'json' : 'md'}`;

    if (format === 'json') {
      content = JSON.stringify(this.currentResearchItems, null, 2);
      mime = "application/json";
    } else {
      content = "# Ambedkar Digital Legacy: Research Citations\n";
      content += `Digital Heritage Archive • Ambedkar International Centre\nExported: ${new Date().toISOString()}\n\n---\n\n`;
      this.currentResearchItems.forEach((item, idx) => {
        content += `### ${idx + 1}. ${item.title}\n`;
        if (item.source_title) content += `**Source**: ${item.source_title}\n`;
        if (item.page) content += `**Page**: ${item.page}\n`;
        if (item.quote) content += `\n> "${item.quote}"\n\n`;
        content += `---\n\n`;
      });
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    this.showToast(`Exported ${filename}`);
  },

  // Document Facsimile / Original Modal
  initDocumentModal() {
    let modal = document.getElementById('archival-doc-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'archival-doc-modal';
      modal.className = 'fixed inset-0 z-50 flex items-center justify-center p-4 hidden';
      modal.innerHTML = `
        <div class="drawer-overlay absolute inset-0" onclick="DAIC.closeDocumentModal()"></div>
        <div class="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] shadow-2xl flex flex-col z-10 border border-[#D7A940]">
          <div class="p-4 bg-[#141F39] text-white flex justify-between items-center rounded-t-lg border-b border-[#D7A940]">
            <div>
              <span id="doc-modal-badge" class="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-[#D7A940] text-[#141F39]">ARCHIVAL RECORD</span>
              <h3 id="doc-modal-title" class="font-heading-cinzel font-bold text-base mt-1">Archival Document Record</h3>
            </div>
            <button onclick="DAIC.closeDocumentModal()" class="text-gray-400 hover:text-white">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div id="doc-modal-body" class="p-6 overflow-y-auto space-y-4 bg-[#F8F4E8] text-sm">
            <!-- Loaded dynamically -->
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }
  },

  async openOriginalDocument(docId, highlightPage = null) {
    const modal = document.getElementById('archival-doc-modal');
    const body = document.getElementById('doc-modal-body');
    const titleEl = document.getElementById('doc-modal-title');
    const badgeEl = document.getElementById('doc-modal-badge');
    if (!modal) return;

    modal.classList.remove('hidden');
    body.innerHTML = `<div class="py-12 text-center text-gray-500">Loading archival repository record for ${docId}...</div>`;

    try {
      const data = await api.getDocument(docId);
      const doc = data.document;
      const chunks = data.chunks || [];

      titleEl.textContent = doc.title;
      badgeEl.textContent = "AUTHENTICATED ARCHIVAL RECORD";

      body.innerHTML = `
        <div class="bg-white p-4 rounded border border-gray-200 shadow-sm grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div class="text-xs text-gray-500 uppercase tracking-wider font-semibold">Archival Provenance</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Institution:</span> ${doc.source_institution}</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Collection:</span> ${doc.collection}</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Document ID:</span> ${doc.id}</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Digitization Method:</span> ${doc.digitization_method || "Archival Scanner"}</div>
          </div>
          <div>
            <div class="text-xs text-gray-500 uppercase tracking-wider font-semibold">Cataloging Details</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Author:</span> ${doc.author}</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Year / Date:</span> ${doc.date_str || doc.year}</div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">Verification Status:</span> <span class="font-bold text-[#3B7558]">${doc.verification_status}</span></div>
            <div class="text-xs font-medium text-[#141F39] mt-1"><span class="text-gray-600">OCR Review Status:</span> ${doc.ocr_status}</div>
          </div>
        </div>

        <div>
          <h4 class="font-bold text-[#141F39] text-xs uppercase tracking-wider mb-2">Summary & Scope</h4>
          <p class="text-xs text-gray-700 bg-white p-3 rounded border border-gray-200">${doc.summary || "Archival document digitized under digital heritage preservation."}</p>
        </div>

        <div>
          <h4 class="font-bold text-[#141F39] text-xs uppercase tracking-wider mb-2">Verified Archival Chunks (${chunks.length} segments)</h4>
          <div class="space-y-3">
            ${chunks.map(c => `
              <div class="p-3 bg-white rounded border ${highlightPage && c.page === parseInt(highlightPage) ? 'border-[#D7A940] bg-[#FFFBF0] ring-1 ring-[#D7A940]' : 'border-gray-200'}">
                <div class="flex justify-between items-center mb-1">
                  <span class="text-xs font-bold text-[#141F39]">${c.section_title || 'Archival Passage'}</span>
                  <span class="text-[10px] bg-[#F4E8C1] text-[#8C5B08] px-2 py-0.5 rounded font-semibold">Page ${c.page}</span>
                </div>
                <p class="text-xs text-gray-800 leading-relaxed font-serif-archival italic mt-1">${c.content}</p>
                <div class="mt-2 flex justify-end space-x-2">
                  <button onclick="DAIC.speakText('${c.content.replace(/'/g, "\\'")}')" class="text-[11px] text-gray-500 hover:text-[#141F39] flex items-center space-x-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
                    <span>Listen</span>
                  </button>
                  <button onclick="DAIC.addToResearch('${doc.title.replace(/'/g, "\\'")}', '${c.content.replace(/'/g, "\\'")}', ${c.page}, '${doc.id}', '${c.id}', '${doc.collection.replace(/'/g, "\\'")}')" class="text-[11px] text-[#D7A940] font-semibold hover:underline">
                    + Add to Research
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } catch (e) {
      body.innerHTML = `<div class="p-6 text-center text-red-600">Failed to load archival document details.</div>`;
    }
  },

  closeDocumentModal() {
    const modal = document.getElementById('archival-doc-modal');
    if (modal) modal.classList.add('hidden');
    this.stopSpeaking();
  },

  // Institutional About the Platform Modal (Replaces Judge Demo)
  initAboutModal() {
    let modal = document.getElementById('about-platform-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'about-platform-modal';
      modal.className = 'fixed inset-0 z-50 flex items-center justify-center p-4 hidden';
      modal.innerHTML = `
        <div class="drawer-overlay absolute inset-0" onclick="DAIC.closeAboutModal()"></div>
        <div class="relative bg-white rounded-lg max-w-3xl w-full max-h-[90vh] shadow-2xl flex flex-col z-10 border-2 border-[#D7A940]">
          <div class="p-4 bg-[#141F39] text-white flex justify-between items-center rounded-t-lg border-b border-[#D7A940]">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#D7A940] text-[#141F39] uppercase">Institutional Architecture</span>
              <h3 class="font-heading-cinzel font-bold text-sm tracking-wide">Ambedkar Digital Legacy: Platform Overview</h3>
            </div>
            <button onclick="DAIC.closeAboutModal()" class="text-gray-400 hover:text-white" aria-label="Close dialog">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="p-6 overflow-y-auto space-y-4 text-xs text-gray-700 bg-[#F8F4E8]">
            <div class="bg-white p-4 rounded border border-[#E2DAC8]">
              <h4 class="font-bold text-[#141F39] text-sm mb-1">Institutional Mission & Heritage Scope</h4>
              <p class="leading-relaxed text-gray-700"><strong>Ambedkar Digital Legacy</strong> is an AI-powered institutional digital heritage archive developed in partnership with the <strong>Ambedkar International Centre</strong>. It addresses fragmented access to Dr. B. R. Ambedkar's voluminous corpus—including writings, speeches, constituent assembly debates, and historical manuscripts—through a verified semantic discovery and evidence-gated knowledge platform.</p>
            </div>

            <div class="bg-white p-4 rounded border border-[#E2DAC8]">
              <h4 class="font-bold text-[#141F39] text-sm mb-2">The 5 Core Archival Pillars</h4>
              <div class="grid grid-cols-1 sm:grid-cols-5 gap-2 text-center text-[11px]">
                <div class="p-2 rounded bg-gray-50 border border-gray-200">
                  <div class="font-bold text-[#D7A940]">01. PRESERVE</div>
                  <div class="text-[10px] text-gray-600 mt-0.5">High-definition facsimiles & OCR</div>
                </div>
                <div class="p-2 rounded bg-gray-50 border border-gray-200">
                  <div class="font-bold text-[#D7A940]">02. DISCOVER</div>
                  <div class="text-[10px] text-gray-600 mt-0.5">Hybrid lexical & semantic search</div>
                </div>
                <div class="p-2 rounded bg-gray-50 border border-gray-200">
                  <div class="font-bold text-[#D7A940]">03. UNDERSTAND</div>
                  <div class="text-[10px] text-gray-600 mt-0.5">Timelines & knowledge maps</div>
                </div>
                <div class="p-2 rounded bg-gray-50 border border-gray-200">
                  <div class="font-bold text-[#D7A940]">04. VERIFY</div>
                  <div class="text-[10px] text-gray-600 mt-0.5">Strict Evidence Gate (No AI Hallucination)</div>
                </div>
                <div class="p-2 rounded bg-gray-50 border border-gray-200">
                  <div class="font-bold text-[#D7A940]">05. LEARN</div>
                  <div class="text-[10px] text-gray-600 mt-0.5">Multilingual audio & visitor kiosk</div>
                </div>
              </div>
            </div>

            <div class="bg-white p-4 rounded border border-[#E2DAC8]">
              <h4 class="font-bold text-[#141F39] text-sm mb-2">7-Step Evidence-Gated Retrieval Pipeline</h4>
              <div class="space-y-2">
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">1</span>
                  <div><strong>Query Processing:</strong> Multi-lingual term sanitization and language routing.</div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">2</span>
                  <div><strong>Lexical Sparse Retrieval (SQLite FTS5 / BM25):</strong> Fast exact term and statute matching (e.g., "Article 17", "Mahad Satyagraha", "labour legislation").</div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">3</span>
                  <div><strong>Dense Semantic Retrieval (FAISS / BGE-M3):</strong> High-dimensional conceptual vector embeddings capturing semantic intent.</div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">4</span>
                  <div><strong>Reciprocal Rank Fusion (RRF):</strong> Fuses sparse and dense ranks via <code>RRF = Σ 1/(k + rank)</code> with k=60.</div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">5</span>
                  <div><strong>Cross-Modal Re-ranking:</strong> Term density and title alignment re-ranking.</div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">6</span>
                  <div><strong>Institutional Evidence Gate:</strong> Strict guardrail testing chunk authenticity against database records, volume/page references, and threshold scores. <em>Rejects unsupported inquiries!</em></div>
                </div>
                <div class="flex items-start space-x-2">
                  <span class="w-5 h-5 rounded-full bg-[#141F39] text-[#D7A940] flex items-center justify-center font-bold text-[10px] shrink-0">7</span>
                  <div><strong>Grounded Synthesis (Gemini / Archival Context):</strong> Generates citation-linked answer directly anchored to primary source records.</div>
                </div>
              </div>
            </div>

            <div class="bg-white p-4 rounded border border-[#E2DAC8] flex justify-between items-center">
              <div>
                <h5 class="font-bold text-[#141F39]">Explore AI Archival Research Assistant</h5>
                <p class="text-[11px] text-gray-500">Ask questions and observe the live evidence verification trace.</p>
              </div>
              <a href="/ask?q=What%20did%20Ambedkar%20say%20about%20labour%20rights%3F" class="px-4 py-2 bg-[#141F39] text-[#D7A940] font-bold rounded shadow hover:bg-[#202E4E] transition-colors border border-[#D7A940]">
                Ask the Archive
              </a>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }
  },

  openAboutModal() {
    const modal = document.getElementById('about-platform-modal');
    if (modal) modal.classList.remove('hidden');
  },

  closeAboutModal() {
    const modal = document.getElementById('about-platform-modal');
    if (modal) modal.classList.add('hidden');
  },

  // Toast Notifications
  showToast(message, type = "info") {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed bottom-5 right-5 z-50 flex flex-col space-y-2';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const isError = type === 'error';
    toast.className = `px-4 py-2.5 rounded shadow-lg text-xs font-medium flex items-center space-x-2 transition-all transform translate-y-2 opacity-0 ${
      isError ? 'bg-red-700 text-white' : 'bg-[#141F39] text-white border border-[#D7A940]'
    }`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  // Speech Recognition (Voice Input) System
  checkVoiceSupport() {
    this.speechSupported = 'speechSynthesis' in window;
    this.recognitionSupported = ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
  },

  startVoiceInput(callbackConfig = {}) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.showToast("Voice recognition is not supported in this browser.", "error");
      if (callbackConfig.onStateChange) callbackConfig.onStateChange('error');
      return false;
    }

    // Stop any active recognition session safely
    this.stopVoiceInput();

    this.recognitionCallback = callbackConfig;
    const lang = this.currentLanguage || 'en';
    const langInfo = this.VOICE_LANG_MAP[lang] || { bcp47: 'en-IN', native: 'English' };

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = langInfo.bcp47; // e.g. en-IN, hi-IN, mr-IN, kn-IN, ta-IN (NO en-US)

      recognition.onstart = () => {
        this.recognitionState = 'listening';
        if (callbackConfig.onStateChange) {
          callbackConfig.onStateChange('listening', langInfo);
        }
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        const currentText = finalTranscript || interimTranscript;
        if (callbackConfig.onTranscript) {
          callbackConfig.onTranscript(currentText, Boolean(finalTranscript));
        }

        if (finalTranscript) {
          this.recognitionState = 'completed';
          if (callbackConfig.onStateChange) {
            callbackConfig.onStateChange('completed', langInfo);
          }
          if (callbackConfig.onFinish) {
            callbackConfig.onFinish(finalTranscript.trim());
          }
        }
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        this.recognitionState = 'error';
        if (callbackConfig.onStateChange) {
          callbackConfig.onStateChange('error', event.error);
        }
      };

      recognition.onend = () => {
        if (this.recognitionState === 'listening') {
          this.recognitionState = 'idle';
        }
        if (callbackConfig.onStateChange) {
          callbackConfig.onStateChange(this.recognitionState, langInfo);
        }
      };

      this.activeRecognition = recognition;
      recognition.start();
      return true;
    } catch (e) {
      console.error("Failed to start speech recognition:", e);
      this.recognitionState = 'error';
      if (callbackConfig.onStateChange) callbackConfig.onStateChange('error');
      return false;
    }
  },

  stopVoiceInput() {
    if (this.activeRecognition) {
      try {
        this.activeRecognition.stop();
      } catch (e) {}
      this.activeRecognition = null;
    }
    this.recognitionState = 'idle';
  },

  // Speech Synthesis (Voice Output) System
  getBestVoiceForLanguage(langCode) {
    if (!('speechSynthesis' in window)) return { voice: null, isNative: false };
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return { voice: null, isNative: false };

    const targetBcp = (this.VOICE_LANG_MAP[langCode] || {}).bcp47 || 'en-IN';
    const targetPrefix = targetBcp.split('-')[0].toLowerCase(); // 'hi', 'mr', 'kn', 'ta', 'en'

    // 1. Exact BCP-47 match
    let exact = voices.find(v => v.lang.toLowerCase().replace('_', '-') === targetBcp.toLowerCase());
    if (exact) return { voice: exact, isNative: true };

    // 2. Language prefix / family match
    let family = voices.find(v => v.lang.toLowerCase().startsWith(targetPrefix));
    if (family) return { voice: family, isNative: true };

    // 3. Indian English voice (e.g. en-IN or containing Indian naming)
    let indianEn = voices.find(v => 
      v.lang.toLowerCase().includes('en-in') || 
      (v.lang.toLowerCase().startsWith('en') && (
        v.name.toLowerCase().includes('india') || 
        v.name.toLowerCase().includes('ravi') || 
        v.name.toLowerCase().includes('heera') || 
        v.name.toLowerCase().includes('neerja')
      ))
    );
    if (indianEn) return { voice: indianEn, isNative: false };

    // 4. System default fallback
    let defaultVoice = voices.find(v => v.default) || voices[0];
    return { voice: defaultVoice, isNative: false };
  },

  speakText(text, rate = null) {
    if (!('speechSynthesis' in window)) {
      this.showToast("Voice narration is not supported on this browser.", "error");
      return;
    }

    // Cancel any previous speech to avoid overlapping
    window.speechSynthesis.cancel();
    this.isSpeaking = false;
    this.isPaused = false;

    if (!text || !text.trim()) return;

    const currentRate = rate !== null ? rate : this.speechRate;
    const lang = this.currentLanguage || 'en';
    const langInfo = this.VOICE_LANG_MAP[lang] || { bcp47: 'en-IN', native: 'English' };

    const { voice, isNative } = this.getBestVoiceForLanguage(lang);

    if (!isNative && lang !== 'en') {
      this.showToast(`Native voice unavailable for ${langInfo.native} on this device. Using available system voice.`);
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = langInfo.bcp47;
    if (voice) utterance.voice = voice;
    utterance.rate = currentRate;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.isPaused = false;
      this.notifySpeechState('playing');
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.isPaused = false;
      this.notifySpeechState('stopped');
    };

    utterance.onerror = (e) => {
      this.isSpeaking = false;
      this.isPaused = false;
      this.notifySpeechState('stopped');
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
    this.notifySpeechState('playing');
  },

  pauseSpeaking() {
    if (window.speechSynthesis && this.isSpeaking && !this.isPaused) {
      window.speechSynthesis.pause();
      this.isPaused = true;
      this.notifySpeechState('paused');
    }
  },

  resumeSpeaking() {
    if (window.speechSynthesis && this.isSpeaking && this.isPaused) {
      window.speechSynthesis.resume();
      this.isPaused = false;
      this.notifySpeechState('playing');
    }
  },

  stopSpeaking() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      this.isSpeaking = false;
      this.isPaused = false;
      this.notifySpeechState('stopped');
    }
  },

  setSpeechRate(rate) {
    this.speechRate = parseFloat(rate);
    if (this.isSpeaking && this.currentUtterance) {
      const text = this.currentUtterance.text;
      this.speakText(text, this.speechRate);
    }
  },

  notifySpeechState(state) {
    window.dispatchEvent(new CustomEvent('daic:speechStateChanged', {
      detail: {
        state: state, // 'playing' | 'paused' | 'stopped'
        rate: this.speechRate,
        language: this.currentLanguage
      }
    }));
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.DAIC.init();
});
