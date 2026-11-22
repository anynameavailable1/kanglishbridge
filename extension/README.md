# Extension

Load unpacked from `chrome://extensions` (Developer mode). Backend must run at http://127.0.0.1:8000.
Files: `popup.*` (UI), `background.js` (context menu + backend relay), `api.js` (backend URL), `content/overlay.*` (result panel), `content/whatsapp.js` (WhatsApp Web; edit `SELECTORS` if it stops working). `icons/make_icons.py` regenerates placeholder icons.
After editing any file, click the reload icon on the extension card and refresh open tabs.
