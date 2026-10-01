/**
 * Ambedkar Digital Heritage Archive - Premium Animated Heritage Background System
 * 
 * Features:
 * 1. 24-spoke Ashoka Chakra slow continuous rotation
 * 2. Archival portrait blending with subtle vignette
 * 3. Floating archival manuscript layers
 * 4. Ultra-lightweight digital knowledge particles canvas (18-25 nodes with connecting hairlines)
 * 5. Smooth mouse parallax (lerped micro-movements)
 * 6. Archival OCR scan-line simulation
 * 7. IntersectionObserver auto-pause & prefers-reduced-motion compliance
 */

(function () {
  'use strict';

  const HeritageBackground = {
    initialized: false,
    reducedMotion: false,
    mouse: { x: 0, y: 0, targetX: 0, targetY: 0 },
    isMouseMoving: false,
    rafId: null,
    particleCanvases: [],

    init() {
      if (this.initialized) return;
      this.initialized = true;

      // Check prefers-reduced-motion
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      this.reducedMotion = mediaQuery.matches;
      mediaQuery.addEventListener('change', (e) => {
        this.reducedMotion = e.matches;
        if (this.reducedMotion) {
          this.stopParallax();
        } else {
          this.startParallax();
        }
      });

      // Init features
      this.initParticles();
      if (!this.reducedMotion && window.innerWidth >= 768) {
        this.initParallax();
      }
    },

    /* ========================================================================
       1. Mouse Parallax (Silky lerp with auto-idle detection)
       ======================================================================== */
    initParallax() {
      let idleTimeout;

      window.addEventListener('mousemove', (e) => {
        const halfW = window.innerWidth / 2;
        const halfH = window.innerHeight / 2;

        this.mouse.targetX = (e.clientX - halfW) / halfW; // -1.0 to 1.0
        this.mouse.targetY = (e.clientY - halfH) / halfH; // -1.0 to 1.0

        if (!this.isMouseMoving) {
          this.isMouseMoving = true;
          this.renderParallax();
        }

        clearTimeout(idleTimeout);
        idleTimeout = setTimeout(() => {
          // Keep loop running until lerp settles
        }, 1200);
      }, { passive: true });
    },

    renderParallax() {
      if (this.reducedMotion) return;

      // Lerp factor
      const factor = 0.05;
      this.mouse.x += (this.mouse.targetX - this.mouse.x) * factor;
      this.mouse.y += (this.mouse.targetY - this.mouse.y) * factor;

      const mx = this.mouse.x;
      const my = this.mouse.y;

      // Parallax depths:
      // Chakra: 4px
      // Portrait: 7px
      // Documents: 10px
      // Particles: 3px
      const chakras = document.querySelectorAll('.ashoka-chakra.parallax-layer');
      chakras.forEach(el => {
        el.style.transform = `translate3d(${(-mx * 4).toFixed(2)}px, ${(-my * 4).toFixed(2)}px, 0)`;
      });

      const portraits = document.querySelectorAll('.ambedkar-portrait.parallax-layer');
      portraits.forEach(el => {
        el.style.transform = `translate3d(${(mx * 7).toFixed(2)}px, ${(my * 7).toFixed(2)}px, 0)`;
      });

      const docs = document.querySelectorAll('.archival-document.parallax-layer');
      docs.forEach(el => {
        el.style.transform = `translate3d(${(mx * 10).toFixed(2)}px, ${(my * 10).toFixed(2)}px, 0)`;
      });

      const particles = document.querySelectorAll('.archive-particles.parallax-layer');
      particles.forEach(el => {
        el.style.transform = `translate3d(${(-mx * 3).toFixed(2)}px, ${(-my * 3).toFixed(2)}px, 0)`;
      });

      // Continue animating if difference is still perceptible
      const dx = Math.abs(this.mouse.targetX - this.mouse.x);
      const dy = Math.abs(this.mouse.targetY - this.mouse.y);

      if (dx > 0.001 || dy > 0.001) {
        this.rafId = requestAnimationFrame(() => this.renderParallax());
      } else {
        this.isMouseMoving = false;
      }
    },

    stopParallax() {
      if (this.rafId) cancelAnimationFrame(this.rafId);
      this.isMouseMoving = false;
      document.querySelectorAll('.parallax-layer').forEach(el => {
        el.style.transform = 'none';
      });
    },

    startParallax() {
      this.isMouseMoving = true;
      this.renderParallax();
    },

    /* ========================================================================
       2. Digital Archive Particles Canvas
       ======================================================================== */
    initParticles() {
      const containers = document.querySelectorAll('.archive-particles');
      containers.forEach(container => {
        this.createParticleCanvas(container);
      });
    },

    createParticleCanvas(container) {
      const canvas = document.createElement('canvas');
      canvas.setAttribute('aria-hidden', 'true');
      canvas.style.display = 'block';
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      canvas.style.pointerEvents = 'none';
      container.appendChild(canvas);

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let width = 0;
      let height = 0;
      let isVisible = true;
      let particles = [];
      const particleCount = window.innerWidth < 640 ? 12 : (window.innerWidth < 1024 ? 18 : 24);

      function resize() {
        const rect = container.getBoundingClientRect();
        width = canvas.width = rect.width || window.innerWidth;
        height = canvas.height = rect.height || 500;
      }

      function initParticleList() {
        particles = [];
        for (let i = 0; i < particleCount; i++) {
          particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.22,
            vy: (Math.random() - 0.5) * 0.22,
            radius: Math.random() * 0.9 + 0.9, // 0.9 to 1.8px
            baseAlpha: Math.random() * 0.035 + 0.03, // 0.03 to 0.065
            pulseSpeed: Math.random() * 0.02 + 0.01,
            pulseVal: Math.random() * Math.PI * 2
          });
        }
      }

      resize();
      initParticleList();

      window.addEventListener('resize', () => {
        resize();
      }, { passive: true });

      // Pause when scrolled offscreen
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          isVisible = entry.isIntersecting;
        });
      }, { threshold: 0.05 });
      observer.observe(container);

      // Render loop
      const reduced = this.reducedMotion;
      function loop() {
        if (!reduced && isVisible && width > 0 && height > 0) {
          ctx.clearRect(0, 0, width, height);

          // Update & draw particles
          for (let i = 0; i < particles.length; i++) {
            const p = particles[i];

            p.x += p.vx;
            p.y += p.vy;

            // Soft wrap around bounds
            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;

            p.pulseVal += p.pulseSpeed;
            const alpha = p.baseAlpha + Math.sin(p.pulseVal) * 0.15;

            // Draw particle point
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(215, 169, 64, ${Math.max(0.1, alpha.toFixed(2))})`;
            ctx.fill();

            // Connect nearby points with delicate hairline
            for (let j = i + 1; j < particles.length; j++) {
              const p2 = particles[j];
              const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
              const maxDist = 95;

              if (dist < maxDist) {
                const lineAlpha = (1 - dist / maxDist) * 0.045;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.strokeStyle = `rgba(215, 169, 64, ${lineAlpha.toFixed(3)})`;
                ctx.lineWidth = 0.65;
                ctx.stroke();
              }
            }
          }
        }
        requestAnimationFrame(loop);
      }

      requestAnimationFrame(loop);
    }
  };

  window.HeritageBackground = HeritageBackground;

  // Initialize as soon as DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => HeritageBackground.init());
  } else {
    HeritageBackground.init();
  }
})();
