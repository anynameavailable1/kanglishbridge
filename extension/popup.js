const $ = (id) => document.getElementById(id);
let last = null; // last successful {source, data}

// ---- theme -------------------------------------------------------------
async function initTheme() {
  const { theme } = await chrome.storage.local.get("theme");
  if (theme) document.documentElement.dataset.theme = theme;
}
$("theme").addEventListener("click", async () => {
  const cur = document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  await chrome.storage.local.set({ theme: next });
});

// ---- backend status ----------------------------------------------------
async function checkHealth() {
  const el = $("status");
  try {
    const h = await KB_API.health();
    if (h.models_ready) { el.dataset.state = "ok"; $("status-text").textContent = `Ready · ${h.device}`; }
    else if (Object.values(h.models).includes("error")) { el.dataset.state = "down"; $("status-text").textContent = "Model error"; }
    else { el.dataset.state = "loading"; $("status-text").textContent = "Loading models…"; }
    el.title = h.message || "";
  } catch (e) {
    el.dataset.state = "down"; $("status-text").textContent = "Backend offline"; el.title = e.message;
  }
}

// ---- translate ---------------------------------------------------------
function setBusy(b) {
  $("translate").disabled = b; $("translate").querySelector(".spinner").hidden = !b;
  $("translate-label").textContent = b ? "Translating…" : "Translate";
}
function showError(msg) { $("error").textContent = msg; $("error").hidden = !msg; }

async function translate() {
  const text = $("input").value.trim();
  if (!text) { showError("Type or paste some text first."); return; }
  showError(""); setBusy(true);
  try {
    const data = await KB_API.translate(text);
    last = { source: text, data };
    $("output").textContent = data.translated_text;
    $("langs").textContent = data.detected_languages.join(" + ") || "—";
    $("normalized").textContent = data.normalized_text;
    const w = $("warnings"); w.replaceChildren();
    data.warnings.forEach((m) => { const li = document.createElement("li"); li.textContent = m; w.appendChild(li); });
    w.hidden = data.warnings.length === 0;
    $("result").hidden = false; $("fb-msg").textContent = "";
  } catch (e) {
    showError(e.message); $("result").hidden = true;
  } finally { setBusy(false); checkHealth(); }
}

$("translate").addEventListener("click", translate);
$("input").addEventListener("keydown", (e) => { if (e.ctrlKey && e.key === "Enter") translate(); });
$("clear").addEventListener("click", () => { $("input").value = ""; $("result").hidden = true; showError(""); $("input").focus(); });
$("copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("output").textContent); $("copy").textContent = "Copied ✓"; }
  catch (e) { showError("Could not access the clipboard."); }
  setTimeout(() => ($("copy").textContent = "Copy"), 1500);
});
$("fb-send").addEventListener("click", async () => {
  const fixed = $("fb-text").value.trim();
  if (!last || !fixed) { $("fb-msg").textContent = "Enter a correction first."; return; }
  try {
    await KB_API.feedback(last.source, last.data.translated_text, fixed);
    $("fb-msg").textContent = "Saved locally. Thank you!"; $("fb-text").value = "";
  } catch (e) { $("fb-msg").textContent = e.message; }
});

initTheme(); checkHealth(); setInterval(checkHealth, 5000); $("input").focus();
