importScripts("api.js");

const MENU_ID = "kb-translate-selection";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: MENU_ID, title: "Translate Selected Text to English", contexts: ["selection"] });
  });
});

function toTab(tabId, message) {
  chrome.tabs.sendMessage(tabId, message).catch((e) => console.warn("[KanglishBridge] could not reach tab:", e.message));
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID || !tab || !tab.id) return;
  const text = (info.selectionText || "").trim();   // only what the user selected
  if (!text) return;
  try {
    await chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ["content/overlay.css"] });
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content/overlay.js"] });
  } catch (e) {
    console.warn("[KanglishBridge] cannot inject into this page (restricted page?):", e.message);
    return;
  }
  toTab(tab.id, { type: "KB_SHOW", state: "loading", source: text });
  try {
    toTab(tab.id, { type: "KB_SHOW", state: "done", source: text, data: await KB_API.translate(text) });
  } catch (e) {
    toTab(tab.id, { type: "KB_SHOW", state: "error", source: text, message: e.message });
  }
});

// Content scripts (WhatsApp module) ask the worker to call the backend, so page origins never talk to localhost.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.type !== "KB_TRANSLATE" || typeof msg.text !== "string") return false;
  KB_API.translate(msg.text)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((e) => sendResponse({ ok: false, error: e.message }));
  return true; // async response
});
