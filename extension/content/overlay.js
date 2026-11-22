// Floating result panel shared by the context menu and the WhatsApp module. Uses textContent only (no innerHTML).
(() => {
  if (window.__kbOverlay) return;

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function close() { const p = document.getElementById("kb-panel"); if (p) p.remove(); }

  /**
   * show({state:'loading'|'done'|'error', source, data, message, onReplace})
   * onReplace (optional): function(translatedText) -> string|undefined error message. Adds a "Replace draft" button.
   */
  function show(opts) {
    close();
    const panel = el("div"); panel.id = "kb-panel"; panel.setAttribute("role", "dialog");
    const head = el("div", "kb-head"); head.append(el("span", "", "KanglishBridge"));
    const x = el("button", "kb-x", "×"); x.title = "Close (Esc)"; x.addEventListener("click", close); head.append(x);
    panel.append(head);

    if (opts.state === "loading") {
      const l = el("div", "kb-note"); l.append(el("span", "kb-spin"), document.createTextNode("Translating…")); panel.append(l);
    } else if (opts.state === "error") {
      panel.append(el("div", "kb-err", opts.message || "Something went wrong."));
    } else {
      const d = opts.data; const out = el("div", "kb-out", d.translated_text); panel.append(out);
      (d.warnings || []).slice(0, 3).forEach((w) => panel.append(el("div", "kb-warn", "⚠ " + w)));
      const note = el("div", "kb-note"); panel.append(note);
      const btns = el("div", "kb-btns");
      const copy = el("button", "kb-btn kb-primary", "Copy");
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(d.translated_text); copy.textContent = "Copied ✓"; }
        catch (_) { note.textContent = "Clipboard blocked; select the text and press Ctrl+C."; }
      });
      btns.append(copy);
      if (typeof opts.onReplace === "function") {
        const rep = el("button", "kb-btn", "Replace draft");
        rep.title = "Puts the translation in the message box. It is never sent automatically.";
        rep.addEventListener("click", () => { const err = opts.onReplace(d.translated_text); note.textContent = err || "Draft replaced. Review it, then send it yourself."; });
        btns.append(rep);
      }
      panel.append(btns);
    }
    document.documentElement.append(panel);
  }

  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); }, true);
  chrome.runtime.onMessage.addListener((msg) => { if (msg && msg.type === "KB_SHOW") show(msg); });
  window.__kbOverlay = { show, close };
})();
