// Shared by the popup (<script>) and the background service worker (importScripts).
// The ONLY place that knows the backend URL.
const KB_API = (() => {
  const BASE = "http://127.0.0.1:8000";

  async function request(path, options = {}, timeoutMs = 120000) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeoutMs);
    try {
      const res = await fetch(BASE + path, { ...options, signal: ctl.signal });
      let body = null;
      try { body = await res.json(); } catch (_) { /* non-JSON error body */ }
      if (!res.ok) {
        const detail = body && typeof body.detail === "string" ? body.detail : "The request was rejected.";
        const err = new Error(detail);
        err.status = res.status;
        throw err;
      }
      return body;
    } catch (err) {
      if (err.name === "AbortError") throw new Error("The backend took too long to respond.");
      if (err instanceof TypeError) throw new Error("Cannot reach the backend at 127.0.0.1:8000. Is it running?");
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  const post = (path, payload, timeout) => request(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }, timeout);

  return {
    health: () => request("/health", {}, 4000),
    translate: (text) => post("/api/v1/translate", { text }),
    feedback: (original_text, model_translation, corrected_translation) =>
      post("/api/v1/feedback", { original_text, model_translation, corrected_translation }, 10000),
  };
})();
