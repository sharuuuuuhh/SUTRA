/**
 * Sutra - Landing Page Interactions & Supabase Google Auth
 */

document.addEventListener("DOMContentLoaded", async () => {
  await initNavAndAuthState();
  initTopProgressBar();
  initPageLoadAnimations();
  initSignaturePinnedMoment();
  initParallaxEffects();
  initIntersectionReveals();
  initStepsTimelineScroll();
  initAuthModal();
});

// ----------------- NAV & AUTH STATE -----------------

async function initNavAndAuthState() {
  const nav = document.querySelector(".site-nav");
  const navActions = document.getElementById("nav-actions");

  window.addEventListener("scroll", () => {
    if (window.scrollY > 12) {
      nav.classList.add("scrolled");
    } else {
      nav.classList.remove("scrolled");
    }
  }, { passive: true });

  const session = await getSupabaseSession();
  if (session) {
    if (navActions) {
      navActions.innerHTML = `
        <a href="/app.html" class="btn btn-primary" id="open-app-nav-btn">Open app</a>
      `;
    }
    const heroCta = document.getElementById("hero-primary-cta");
    if (heroCta) {
      heroCta.textContent = "Open app";
      heroCta.href = "/app.html";
      heroCta.removeAttribute("data-open-modal");
    }
    const finalCta = document.getElementById("final-cta-btn");
    if (finalCta) {
      finalCta.textContent = "Open app";
      finalCta.href = "/app.html";
      finalCta.removeAttribute("data-open-modal");
    }
  }
}

// ----------------- TOP PROGRESS BAR -----------------

function initTopProgressBar() {
  const progressBar = document.getElementById("scroll-progress-bar");
  if (!progressBar) return;

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (totalHeight > 0) {
          const progress = (window.scrollY / totalHeight) * 100;
          progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });
}

// ----------------- 1. PAGE LOAD ANIMATIONS -----------------

function initPageLoadAnimations() {
  if (document.documentElement.classList.contains("rm") || typeof anime === "undefined") {
    return;
  }

  const tl = anime.timeline({
    easing: "easeOutCubic",
    duration: 800
  });

  tl.add({
    targets: ".headline-line",
    translateY: ["100%", "0%"],
    opacity: [0, 1],
    delay: anime.stagger(140),
    duration: 900
  })
  .add({
    targets: [".hero-subtitle", ".hero-actions", ".hero-pill"],
    translateY: [20, 0],
    opacity: [0, 1],
    delay: anime.stagger(100),
    duration: 650
  }, "-=500")
  .add({
    targets: ".hero-visual .paper-sheet",
    translateY: [40, 0],
    rotate: [-5, -2.5],
    opacity: [0, 1],
    duration: 900,
    easing: "easeOutElastic(1, .8)"
  }, "-=600")
  .add({
    targets: ".sweep-highlight",
    scaleX: [0, 1],
    opacity: [0, 1],
    duration: 600,
    delay: anime.stagger(150),
    easing: "easeOutQuart"
  }, "-=400")
  .add({
    targets: ".sticky-note",
    scale: [0.8, 1],
    rotate: [0, 5],
    opacity: [0, 1],
    duration: 500,
    easing: "easeOutBack"
  }, "-=300");
}

// ----------------- 2. SIGNATURE MOMENT (PINNED 340vh SCROLL) -----------------

function initSignaturePinnedMoment() {
  const section = document.getElementById("signature-pinned-section");
  if (!section) return;

  const rawSheet = document.getElementById("raw-notes-sheet");
  const cleanSheet = document.getElementById("clean-notes-sheet");
  const fillerTexts = document.querySelectorAll(".filler-text");
  const phrases = document.querySelectorAll(".highlightable-phrase");
  const cleanItems = document.querySelectorAll(".clean-item");
  const indicators = document.querySelectorAll(".pinned-step-indicator");

  if (document.documentElement.classList.contains("rm") || typeof anime === "undefined") {
    fillerTexts.forEach(el => el.style.opacity = "0.2");
    phrases.forEach(el => el.style.backgroundColor = "var(--color-highlighter)");
    if (cleanSheet) {
      cleanSheet.style.transform = "translateY(0)";
      cleanSheet.style.opacity = "1";
    }
    cleanItems.forEach(el => {
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
    return;
  }

  const pinTl = anime.timeline({
    autoplay: false,
    easing: "linear"
  });

  pinTl.add({
    targets: phrases,
    backgroundColor: ["rgba(255, 225, 77, 0)", "rgba(255, 225, 77, 1)"],
    duration: 300,
    delay: anime.stagger(100)
  })
  .add({
    targets: fillerTexts,
    opacity: [1, 0.16],
    duration: 300
  }, "+=100")
  .add({
    targets: rawSheet,
    scale: [1, 0.94],
    opacity: [1, 0.85],
    duration: 300
  }, "-=300")
  .add({
    targets: cleanSheet,
    translateY: [60, 0],
    opacity: [0.2, 1],
    duration: 400
  }, "+=50")
  .add({
    targets: cleanItems,
    translateY: [15, 0],
    opacity: [0, 1],
    duration: 300,
    delay: anime.stagger(100)
  }, "-=200");

  let ticking = false;

  function updatePinnedScroll() {
    const rect = section.getBoundingClientRect();
    const totalDist = section.offsetHeight - window.innerHeight;
    if (totalDist <= 0) return;

    const scrolled = -rect.top;
    const progress = Math.max(0, Math.min(1, scrolled / totalDist));

    pinTl.seek(pinTl.duration * progress);

    if (indicators.length === 3) {
      indicators.forEach(ind => ind.classList.remove("active"));
      if (progress < 0.33) {
        indicators[0].classList.add("active");
      } else if (progress < 0.68) {
        indicators[1].classList.add("active");
      } else {
        indicators[2].classList.add("active");
      }
    }
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updatePinnedScroll();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  updatePinnedScroll();
}

// ----------------- 3. PARALLAX DRIFT -----------------

function initParallaxEffects() {
  if (document.documentElement.classList.contains("rm")) return;

  const parallaxElements = document.querySelectorAll("[data-parallax-speed]");
  if (!parallaxElements.length) return;

  let ticking = false;

  function updateParallax() {
    parallaxElements.forEach(el => {
      const speed = parseFloat(el.getAttribute("data-parallax-speed") || "0.1");
      const rect = el.parentElement.getBoundingClientRect();
      const viewCenter = window.innerHeight / 2;
      const elementCenter = rect.top + rect.height / 2;
      const offset = (elementCenter - viewCenter) * speed;

      el.style.translate = `0px ${offset.toFixed(1)}px`;
    });
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateParallax();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });
}

// ----------------- 4. REVEAL ON ENTER -----------------

function initIntersectionReveals() {
  const revealElements = document.querySelectorAll(".reveal-on-scroll");
  if (!revealElements.length) return;

  if (document.documentElement.classList.contains("rm") || !("IntersectionObserver" in window)) {
    revealElements.forEach(el => {
      el.style.opacity = "1";
      el.style.transform = "none";
    });
    document.querySelectorAll(".prob-fill").forEach(fill => {
      fill.style.width = fill.getAttribute("data-target-width") || "70%";
    });
    return;
  }

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const target = entry.target;
        
        if (typeof anime !== "undefined") {
          anime({
            targets: target,
            translateY: [28, 0],
            opacity: [0, 1],
            duration: 750,
            easing: "easeOutCubic"
          });

          const bars = target.querySelectorAll(".prob-fill");
          if (bars.length > 0) {
            bars.forEach(bar => {
              const targetWidth = bar.getAttribute("data-target-width") || "70%";
              setTimeout(() => {
                bar.style.width = targetWidth;
              }, 200);
            });
          }

          const ctaHighlight = target.querySelector(".cta-sweep");
          if (ctaHighlight) {
            anime({
              targets: ctaHighlight,
              scaleX: [0, 1],
              opacity: [0, 1],
              duration: 700,
              delay: 300,
              easing: "easeOutQuart"
            });
          }
        } else {
          target.style.opacity = "1";
          target.style.transform = "none";
        }

        obs.unobserve(target);
      }
    });
  }, { threshold: 0.15 });

  revealElements.forEach(el => {
    el.style.opacity = "0";
    el.style.transform = "translateY(28px)";
    observer.observe(el);
  });
}

// ----------------- 5. THREE STEPS TIMELINE -----------------

function initStepsTimelineScroll() {
  const timelineFill = document.getElementById("steps-timeline-fill");
  const section = document.getElementById("steps-section");
  if (!timelineFill || !section) return;

  if (document.documentElement.classList.contains("rm")) {
    timelineFill.style.transform = "scaleY(1)";
    return;
  }

  let ticking = false;

  function updateStepsFill() {
    const rect = section.getBoundingClientRect();
    const windowH = window.innerHeight;
    
    const startY = windowH * 0.75;
    const currentY = rect.top;
    const totalDist = rect.height;

    let progress = (startY - currentY) / totalDist;
    progress = Math.max(0, Math.min(1, progress));

    timelineFill.style.transform = `scaleY(${progress})`;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateStepsFill();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });
}

// ----------------- AUTH MODAL & GOOGLE OAUTH -----------------

function initAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;

  const openBtns = document.querySelectorAll("[data-open-modal]");
  const closeBtn = document.getElementById("modal-close-btn");
  const googleBtn = document.getElementById("google-signin-btn");
  const loginTab = document.getElementById("tab-login");
  const signupTab = document.getElementById("tab-signup");
  const loginForm = document.getElementById("form-login");
  const signupForm = document.getElementById("form-signup");

  function openAuthDialog(mode = "login") {
    switchTab(mode);
    modal.showModal();
  }

  function closeAuthDialog() {
    modal.close();
  }

  function switchTab(mode) {
    if (mode === "login") {
      loginTab.classList.add("active");
      signupTab.classList.remove("active");
      loginForm.style.display = "block";
      signupForm.style.display = "none";
    } else {
      signupTab.classList.add("active");
      loginTab.classList.remove("active");
      signupForm.style.display = "block";
      loginForm.style.display = "none";
    }
  }

  openBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const mode = btn.getAttribute("data-mode") || "login";
      openAuthDialog(mode);
    });
  });

  if (closeBtn) closeBtn.addEventListener("click", closeAuthDialog);
  if (loginTab) loginTab.addEventListener("click", () => switchTab("login"));
  if (signupTab) signupTab.addEventListener("click", () => switchTab("signup"));

  modal.addEventListener("click", (e) => {
    const rect = modal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX && e.clientX <= rect.left + rect.width
    );
    if (!isInDialog) modal.close();
  });

  // Google OAuth Login
  if (googleBtn) {
    googleBtn.addEventListener("click", async () => {
      try {
        googleBtn.disabled = true;
        googleBtn.innerHTML = `<span>Connecting to Google...</span>`;
        
        const sb = await initSupabase();
        if (!sb) {
          throw new Error("Supabase client is initializing. Please try again.");
        }

        const redirectTo = `${window.location.origin}/app.html`;
        const { data, error } = await sb.auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo: redirectTo
          }
        });

        if (error) throw error;
      } catch (err) {
        showToast(err.message || "Could not connect to Google authentication.", "error", 6000);
        googleBtn.disabled = false;
        googleBtn.innerHTML = `<span>Continue with Google</span>`;
      }
    });
  }

  // Email Sign In Form
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = loginForm.querySelector("button[type='submit']");
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;

      submitBtn.disabled = true;
      submitBtn.textContent = "Signing in...";

      try {
        const sb = await initSupabase();
        const { data, error } = await sb.auth.signInWithPassword({ email, password });
        if (error) throw error;

        showToast("Signed in successfully!", "success");
        setTimeout(() => {
          window.location.href = "/app.html";
        }, 400);
      } catch (err) {
        showToast(err.message || "Failed to sign in. Check email and password.", "error", 6000);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Sign in with Email";
      }
    });
  }

  // Email Sign Up Form
  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = signupForm.querySelector("button[type='submit']");
      const name = document.getElementById("signup-name").value.trim();
      const email = document.getElementById("signup-email").value.trim();
      const password = document.getElementById("signup-password").value;

      if (password.length < 8) {
        showToast("Password must be at least 8 characters long.", "error");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Creating account...";

      try {
        const sb = await initSupabase();
        const { data, error } = await sb.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: name, name: name }
          }
        });
        if (error) throw error;

        showToast("Account created! Redirecting...", "success");
        setTimeout(() => {
          window.location.href = "/app.html";
        }, 400);
      } catch (err) {
        showToast(err.message || "Failed to create account.", "error", 6000);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Create account";
      }
    });
  }
}
