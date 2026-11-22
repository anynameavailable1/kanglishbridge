/**
 * WhatsApp Web module - ISOLATED so a WhatsApp DOM change can only break this file.
 *
 * Privacy / safety rules (enforced by construction):
 *  - Reads text ONLY when the user clicks the floating button or presses Alt+T.
 *  - Only reads the user's current text selection, or (Alt+T with nothing selected) the draft in the composer.
 *  - Never walks the chat history, never uses MutationObserver, never stores or logs message text.
 *  - Never clicks Send and never dispatches Enter. "Replace draft" only edits the composer text.
 *
 * If WhatsApp changes its markup, edit the SELECTORS below. The popup always works as a fallback.
 */
(() => {
  if (window.__kbWhatsApp) return;
  window.__kbWhatsApp = true;

  const SELECTORS = {
    composer: ['footer div[contenteditable="true"]', 'div[contenteditable="true"][role="textbox"]'],
    conversation: ["#main", 'div[role="application"]'],
  };
  const log = (...a) => console.warn("[KanglishBridge/WhatsApp]", ...a);
  const first = (list) => { for (const s of list) { const n = document.querySelector(s); if (n) return n; } return null; };

  const fab = document.createElement("div");
  fab.id = "kb-fab"; fab.textContent = "Translate"; fab.setAttribute("role", "button");
  document.documentElement.append(fab);

  let pending = null; // {text, range, where}

  function readSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    const text = sel.toString().trim();
    if (!text) return null;
    const node = sel.anchorNode;
    const composer = first(SELECTORS.composer), convo = first(SELECTORS.conversation);
    if (composer && composer.contains(node)) return { text, range: sel.getRangeAt(0).cloneRange(), where: "composer" };
    if (convo && convo.contains(node)) return { text, range: null, where: "message" };
    return null; // selections elsewhere (search box, etc.) are ignored
  }

  function readDraft() {
    const composer = first(SELECTORS.composer);
    if (!composer || !composer.contains(document.activeElement) && document.activeElement !== composer) return null;
    const text = (composer.innerText || "").trim();
    return text ? { text, range: null, where: "draft" } : null;
  }

  function replaceInComposer(translated, ctx) {
    const composer = first(SELECTORS.composer);
    if (!composer) return "Could not find the message box. Use Copy instead.";
    try {
      composer.focus();
      const sel = window.getSelection();
      if (ctx.where === "composer" && ctx.range) { sel.removeAllRanges(); sel.addRange(ctx.range); }
      else { document.execCommand("selectAll", false); }
      const ok = document.execCommand("insertText", false, translated);
      if (!ok || !(composer.innerText || "").includes(translated.slice(0, 10))) {
        return "WhatsApp blocked automatic replacement. Use Copy and paste it yourself.";
      }
      return undefined;
    } catch (e) {
      log("replace failed:", e.message);
      return "Could not replace the draft. Use Copy instead.";
    }
  }

  async function translate(ctx) {
    fab.style.display = "none";
    window.__kbOverlay.show({ state: "loading" });
    try {
      const res = await chrome.runtime.sendMessage({ type: "KB_TRANSLATE", text: ctx.text });
      if (!res || !res.ok) throw new Error((res && res.error) || "No response from the extension.");
      const canReplace = ctx.where === "composer" || ctx.where === "draft";
      window.__kbOverlay.show({ state: "done", data: res.data, onReplace: canReplace ? (t) => replaceInComposer(t, ctx) : undefined });
    } catch (e) {
      const msg = /context invalidated/i.test(e.message) ? "The extension was reloaded. Refresh this tab." : e.message;
      window.__kbOverlay.show({ state: "error", message: msg });
    }
  }

  document.addEventListener("mouseup", (e) => {
    if (e.target === fab) return;
    setTimeout(() => {                       // let the browser finalise the selection
      try {
        pending = readSelection();
        if (!pending) { fab.style.display = "none"; return; }
        const r = window.getSelection().getRangeAt(0).getBoundingClientRect();
        fab.style.left = Math.max(8, Math.min(window.innerWidth - 100, r.left)) + "px";
        fab.style.top = Math.max(8, r.top - 36) + "px";
        fab.style.display = "block";
      } catch (err) { log("selection handling failed:", err.message); }
    }, 0);
  }, true);

  fab.addEventListener("mousedown", (e) => e.preventDefault());     // keep the selection alive
  fab.addEventListener("click", () => { if (pending) translate(pending); });

  document.addEventListener("keydown", (e) => {
    if (!(e.altKey && !e.ctrlKey && !e.metaKey && e.key.toLowerCase() === "t")) return;
    const ctx = readSelection() || readDraft();
    if (!ctx) return;
    e.preventDefault();
    translate(ctx);
  }, true);

  document.addEventListener("scroll", () => { fab.style.display = "none"; }, true);
})();
