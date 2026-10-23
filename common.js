/* common.js - shared behaviour for the tutorial and lab pages:
   font-size control (14-36px, remembered in localStorage), info popups, official-doc links, small helpers. */
(function () {
  "use strict";
  const LS_FONT = "grocery.fontSize";
  const MIN = 14, MAX = 36, STEP = 2;

  function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function safeSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }

  // ---------- font size
  function applyFont(px) {
    px = Math.max(MIN, Math.min(MAX, px));
    document.documentElement.style.fontSize = px + "px";
    document.querySelectorAll("[data-font-value]").forEach((el) => (el.textContent = px + "px"));
    safeSet(LS_FONT, String(px));
    return px;
  }
  function currentFont() { return parseInt(document.documentElement.style.fontSize) || parseInt(safeGet(LS_FONT)) || 16; }
  window.fontBigger = () => applyFont(currentFont() + STEP);
  window.fontSmaller = () => applyFont(currentFont() - STEP);
  window.fontReset = () => applyFont(16);

  // ---------- official documentation links (used by popups and footers)
  window.DOC_LINKS = {
    ollama: ["Ollama website and downloads", "https://ollama.com/download"],
    ollamaApi: ["Ollama REST API reference", "https://github.com/ollama/ollama/blob/main/docs/api.md"],
    ollamaFaq: ["Ollama FAQ (CORS, OLLAMA_ORIGINS, environment variables)", "https://github.com/ollama/ollama/blob/main/docs/faq.md"],
    deepseek: ["deepseek-r1 model page on Ollama", "https://ollama.com/library/deepseek-r1"],
    gemma: ["gemma3 model page on Ollama", "https://ollama.com/library/gemma3"],
    llama: ["llama3.2 model page on Ollama", "https://ollama.com/library/llama3.2"],
    python: ["Python downloads", "https://www.python.org/downloads/"],
    go: ["Go downloads", "https://go.dev/dl/"],
    localStorage: ["MDN: Window.localStorage", "https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage"],
    fetch: ["MDN: Fetch API", "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API"],
    cors: ["MDN: Cross-Origin Resource Sharing (CORS)", "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"],
    tailwind: ["Tailwind CSS documentation", "https://tailwindcss.com/docs"],
    wilson: ["Wikipedia: Wilson score interval", "https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval"],
    hallucination: ["Wikipedia: Hallucination (artificial intelligence)", "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)"],
    llm: ["Wikipedia: Large language model", "https://en.wikipedia.org/wiki/Large_language_model"],
    markdown: ["Markdown guide", "https://www.markdownguide.org/basic-syntax/"],
    plex: ["IBM Plex typeface", "https://www.ibm.com/plex/"],
  };
  function linkList(keys) {
    return "<ul class='list-disc ml-5 mt-3 space-y-1'>" + keys.map((k) => {
      const [label, url] = window.DOC_LINKS[k];
      return `<li><a class="text-blue-700 underline break-all" target="_blank" rel="noopener" href="${url}">${label}</a></li>`;
    }).join("") + "</ul>";
  }

  // ---------- popup (modal) for "more info"
  function ensureModal() {
    let m = document.getElementById("info-modal");
    if (m) return m;
    m = document.createElement("div");
    m.id = "info-modal";
    m.className = "fixed inset-0 z-50 hidden items-start justify-center bg-black/50 p-4 overflow-y-auto";
    m.innerHTML = `
      <div class="bg-white w-full max-w-2xl mt-8 border-t-4 border-blue-700 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="info-modal-title">
        <div class="flex items-start justify-between p-4 border-b border-gray-200">
          <h3 id="info-modal-title" class="text-xl font-semibold text-blue-900"></h3>
          <button type="button" onclick="closeInfo()" aria-label="Close" class="ml-4 px-3 py-1 text-2xl leading-none text-gray-700 hover:bg-gray-100">&times;</button>
        </div>
        <div id="info-modal-body" class="p-4 text-gray-900 leading-relaxed"></div>
        <div class="p-4 border-t border-gray-200 text-right">
          <button type="button" onclick="closeInfo()" class="px-4 py-2 bg-blue-700 text-white hover:bg-blue-800">Close</button>
        </div>
      </div>`;
    m.addEventListener("click", (e) => { if (e.target === m) window.closeInfo(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") window.closeInfo(); });
    document.body.appendChild(m);
    return m;
  }
  window.showInfo = function (title, html, linkKeys) {
    const m = ensureModal();
    m.querySelector("#info-modal-title").textContent = title;
    m.querySelector("#info-modal-body").innerHTML = html + (linkKeys && linkKeys.length ? "<p class='mt-4 font-semibold'>Official docs and references</p>" + linkList(linkKeys) : "");
    m.classList.remove("hidden"); m.classList.add("flex");
    m.querySelector("button").focus();
  };
  window.closeInfo = function () { const m = document.getElementById("info-modal"); if (m) { m.classList.add("hidden"); m.classList.remove("flex"); } };
  // Any element with data-info="key" opens the popup defined in window.INFO[key] = {title, html, links}
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-info]");
    if (!el) return;
    e.preventDefault();
    const info = (window.INFO || {})[el.dataset.info];
    if (info) window.showInfo(info.title, info.html, info.links);
  });

  // ---------- helpers
  window.escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  window.lsGet = safeGet; window.lsSet = safeSet;
  window.hashInt = function (str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };

  // ---------- init
  document.addEventListener("DOMContentLoaded", () => {
    applyFont(parseInt(safeGet(LS_FONT)) || 16);
    const y = document.getElementById("year"); if (y) y.textContent = new Date().getFullYear();
  });
})();
