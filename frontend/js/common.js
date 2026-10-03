/**
 * Sutra - Common Utilities & Supabase Auth Helpers
 */

let _supabaseClient = null;
let _supabaseConfigPromise = null;

// ----------------- SUPABASE CLIENT INITIALIZATION -----------------

async function initSupabase() {
  if (_supabaseClient) return _supabaseClient;
  if (_supabaseConfigPromise) return await _supabaseConfigPromise;

  _supabaseConfigPromise = (async () => {
    let url = "";
    let anonKey = "";

    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const data = await res.json();
        url = data.supabaseUrl;
        anonKey = data.supabaseAnonKey;
      }
    } catch (e) {
      console.warn("Could not fetch Supabase config from /api/config:", e);
    }

    // Default or fallback placeholder if not set
    if (!url || !anonKey || url.startsWith("your_")) {
      url = window.SUPABASE_URL || "https://placeholder-project.supabase.co";
      anonKey = window.SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.placeholder";
    }

    if (window.supabase && typeof window.supabase.createClient === "function") {
      _supabaseClient = window.supabase.createClient(url, anonKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true
        }
      });
    } else {
      console.error("Supabase JS SDK library not loaded on page.");
    }
    return _supabaseClient;
  })();

  return await _supabaseConfigPromise;
}

async function getSupabaseSession() {
  const sb = await initSupabase();
  if (sb) {
    try {
      const { data, error } = await sb.auth.getSession();
      if (!error && data && data.session) {
        return data.session;
      }
    } catch (e) {
      console.warn("Supabase session check error:", e);
    }
  }

  // Fallback demo session from localStorage
  const fallbackToken = localStorage.getItem("sutra_auth_token");
  if (fallbackToken) {
    const fallbackName = localStorage.getItem("sutra_user_name") || "KTU Scholar";
    return {
      access_token: fallbackToken,
      user: {
        id: "demo-user-ktu",
        email: "scholar@ktu.edu",
        user_metadata: { full_name: fallbackName, name: fallbackName }
      }
    };
  }

  return null;
}

async function getSupabaseUser() {
  const session = await getSupabaseSession();
  return session ? session.user : null;
}

async function signOutUser() {
  const sb = await initSupabase();
  if (sb) {
    await sb.auth.signOut();
  }
  localStorage.removeItem("sutra_auth_token");
  localStorage.removeItem("sutra_user_name");
  window.location.href = "/";
}

// ----------------- TOAST SYSTEM -----------------

function showToast(message, type = "info", duration = 4000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    container.setAttribute("aria-live", "polite");
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  const textSpan = document.createElement("span");
  textSpan.textContent = message;
  toast.appendChild(textSpan);

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.style.background = "none";
  closeBtn.style.border = "none";
  closeBtn.style.color = "inherit";
  closeBtn.style.cursor = "pointer";
  closeBtn.style.fontSize = "1.2rem";
  closeBtn.style.lineHeight = "1";
  closeBtn.style.opacity = "0.75";
  closeBtn.setAttribute("aria-label", "Close toast");
  closeBtn.innerHTML = "&times;";
  closeBtn.addEventListener("click", () => toast.remove());
  toast.appendChild(closeBtn);

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      toast.style.transition = "all 0.25s ease";
      setTimeout(() => toast.remove(), 250);
    }
  }, duration);
}

// ----------------- API CLIENT (SUPABASE BEARER TOKEN) -----------------

async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  const session = await getSupabaseSession();

  if (session && session.access_token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(endpoint, {
    ...options,
    headers: headers
  });

  if (response.status === 401) {
    if (!window.location.pathname.endsWith("/") && !window.location.pathname.endsWith("/index.html")) {
      window.location.href = "/";
    }
    throw new Error("Session expired. Please sign in again.");
  }

  let data;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = (data && data.detail) ? data.detail : `Server error (${response.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

// ----------------- MARKDOWN + KATEX MATH RENDERER -----------------

function renderMarkdownWithKaTeX(rawMarkdown) {
  if (!rawMarkdown) return "";

  const mathPlaceholders = [];
  let placeholderIndex = 0;

  // Protect display math $$...$$
  let processed = rawMarkdown.replace(/\$\$([\s\S]*?)\$\$/g, (match, mathContent) => {
    const placeholder = `%%DISPLAYMATH_${placeholderIndex}%%`;
    placeholderIndex++;
    try {
      if (typeof katex !== "undefined") {
        const rendered = katex.renderToString(mathContent.trim(), { displayMode: true, throwOnError: false });
        mathPlaceholders.push({ placeholder, rendered });
      } else {
        mathPlaceholders.push({ placeholder, rendered: `$$${mathContent}$$` });
      }
    } catch (e) {
      mathPlaceholders.push({ placeholder, rendered: `$$${mathContent}$$` });
    }
    return placeholder;
  });

  // Protect inline math $...$
  processed = processed.replace(/\$([^\$\n]+?)\$/g, (match, mathContent) => {
    const placeholder = `%%INLINEMATH_${placeholderIndex}%%`;
    placeholderIndex++;
    try {
      if (typeof katex !== "undefined") {
        const rendered = katex.renderToString(mathContent.trim(), { displayMode: false, throwOnError: false });
        mathPlaceholders.push({ placeholder, rendered });
      } else {
        mathPlaceholders.push({ placeholder, rendered: `$${mathContent}$` });
      }
    } catch (e) {
      mathPlaceholders.push({ placeholder, rendered: `$${mathContent}$` });
    }
    return placeholder;
  });

  // Parse Markdown with marked
  if (typeof marked !== "undefined") {
    marked.setOptions({
      gfm: true,
      breaks: true,
      headerIds: true
    });
    processed = marked.parse(processed);
  }

  // Restore math placeholders
  mathPlaceholders.forEach(item => {
    processed = processed.split(item.placeholder).join(item.rendered);
  });

  // Sanitize via DOMPurify
  if (typeof DOMPurify !== "undefined") {
    processed = DOMPurify.sanitize(processed, {
      ADD_TAGS: ["math", "annotation", "semantics", "mtext", "mn", "mo", "mi", "mspace", "mover", "munder", "msubsup", "msup", "msub", "mfrac", "mtable", "mtr", "mtd", "mrow"],
      ADD_ATTR: ["display", "xmlns", "columnalign", "rowalign", "mathvariant", "scriptlevel", "linethickness"]
    });
  }

  return processed;
}

// ----------------- REDUCED MOTION DETECTION -----------------
function initMotionPreference() {
  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (mediaQuery.matches) {
    document.documentElement.classList.add("rm");
    document.documentElement.classList.remove("anim");
  } else {
    document.documentElement.classList.add("anim");
    document.documentElement.classList.remove("rm");
  }

  mediaQuery.addEventListener("change", (e) => {
    if (e.matches) {
      document.documentElement.classList.add("rm");
      document.documentElement.classList.remove("anim");
    } else {
      document.documentElement.classList.add("anim");
      document.documentElement.classList.remove("rm");
    }
  });
}

initMotionPreference();
