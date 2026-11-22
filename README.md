# KanglishBridge

Chrome extension + local Python backend that turns Romanized Kannada-English ("Kanglish") into natural English.

```
"Naanu ivattu college ge baralla, swalpa work ide."  ->  "I'm not coming to college today. I have some work to do."
```
(That output is the *goal*; actual wording comes from the IndicTrans2 model and will vary. See "Status".)

## 1. How it works

```
text -> clean -> split sentences -> token router -> IndicXlit -> IndicTrans2 (kan_Knda -> eng_Latn) -> English
                                    (English/names/numbers kept as-is)   (Romanized Kannada words -> Kannada script)
```
No hard-coded translations and no rule-based fallbacks: if the models are not loaded the API returns 503.

## 2. Status - read this first (honest)

| Part | State |
|---|---|
| Token routing, sentence pipeline, dataset tools, split/validation | Written **and tested** (26 unit tests pass, with fake models, in a sandbox) |
| Extension API client (offline / 503 / 422 / success paths) | Tested with a Node mock server |
| FastAPI endpoints (`backend/tests/test_api.py`) | Written; **not run** in the build sandbox (no network to install FastAPI). Run them yourself |
| **IndicXlit + IndicTrans2 integration** | Written from the official model-card/repo usage; **never executed by the author** (no network, no model download). First real run is yours: `KB_RUN_MODEL_TESTS=1` tests exist for exactly this |
| Chrome popup, context menu, WhatsApp module | Written, JS syntax-checked; **not tested in a real Chrome / WhatsApp Web** |
| `scripts/evaluate.py` | Written, syntax-checked; needs the models + sacrebleu to run |
| IndicTrans2 fine-tuning script | **Not included.** `train_transliterator.py` only *prepares* word pairs; see limitation notes |
| Sample dataset | 20 rows, **synthetic, not verified by a native speaker**. Never quote its scores as real performance |

Expect some debugging on first model run (dependency versions are the usual culprit, see Troubleshooting).

## 3. Where things are

| Path | What it is |
|---|---|
| `backend/app/main.py` | FastAPI app, loads models once in the background, CORS, shutdown |
| `backend/app/config.py` | All settings (env vars `KB_*`) |
| `backend/app/api/` | `translate.py`, `health.py`, `feedback.py` (+ token override), `datasets.py` |
| `backend/app/nlp/language_detector.py` | Script-level tokenizer, sentence splitter, whitespace cleaning |
| `backend/app/nlp/token_router.py` | English vs Romanized-Kannada vs name routing rules |
| `backend/app/nlp/transliterator.py` | IndicXlit wrapper (Romanized Kannada -> Kannada script) |
| `backend/app/nlp/translator.py` | IndicTrans2 wrapper (Kannada -> English) |
| `backend/app/nlp/pipeline.py` | Glues the steps together; `build_default_pipeline()` loads real models |
| `backend/app/nlp/base.py` | Adapter interfaces: implement these to swap in a newer model |
| `backend/app/data_tools.py` | Dataset loading, validation, dedupe, seeded split |
| `backend/data/english_vocab.txt` | **Editable** English words that are never transliterated |
| `backend/data/kannada_hints.txt` | **Editable** known Romanized-Kannada words (fixes collisions) |
| `backend/data/token_overrides.json` | **Editable** manual per-word corrections (also via API) |
| `backend/data/feedback.jsonl` | User corrections (created on first feedback; local only) |
| `backend/scripts/` | `validate_dataset.py`, `prepare_dataset.py`, `evaluate.py`, `train_transliterator.py` |
| `backend/tests/` | Unit + API + real-model tests |
| `extension/manifest.json` | MV3 manifest |
| `extension/popup.*` | Popup UI (HTML/CSS/JS) |
| `extension/background.js` | Context menu + relays requests to the backend |
| `extension/api.js` | The only file containing the backend URL |
| `extension/content/overlay.*` | Floating result panel |
| `extension/content/whatsapp.js` | WhatsApp Web module (isolated; edit `SELECTORS` if WhatsApp changes) |
| `datasets/sample/` | Synthetic demo data + its warning README |
| `results/` | Evaluation output goes here |
| `docs/LIMITATIONS.md` | Known failure modes |

Open the `kanglishbridge` folder in VS Code (`code .`). Everything is plain Python/JS.

## 4. Install (Windows PowerShell)

Prerequisites: Python **3.10** (`py -0` lists installed versions), Git, Google Chrome, ~3 GB free disk.

```powershell
cd kanglishbridge\backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install --upgrade pip
pip install -r requirements.txt

# run the tests that need no models
python -m unittest discover -s tests -t .
```

### Model installation
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu     # CPU. For NVIDIA GPU use the selector at pytorch.org
pip install -r requirements-models.txt
```
**Windows caveat:** `ai4bharat-transliteration` (IndicXlit) depends on `fairseq`, which commonly fails to build on native Windows and on Python >= 3.11. IndicTransToolkit also compiles a small extension (needs Visual Studio Build Tools). If installation fails, use **WSL2** (not tested by the author):

```powershell
wsl --install -d Ubuntu          # reboot if asked, then open "Ubuntu"
```
Inside Ubuntu (22.04 ships Python 3.10):
```bash
sudo apt update && sudo apt install -y python3.10-venv build-essential git
cd /mnt/c/path/to/kanglishbridge/backend      # or copy the project into ~/ for faster disk
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-models.txt
```
Chrome on Windows can reach a WSL2 server at `127.0.0.1:8000` through WSL's localhost forwarding.

### Check the real models (first run downloads them)
```powershell
$env:KB_RUN_MODEL_TESTS = "1"
python -m unittest tests.test_real_models -v
```
### Start the backend
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Models load in the background; `http://127.0.0.1:8000/health` shows `"models_ready": true` when done. API docs: `/docs`.

### Load the extension
1. Chrome -> `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** -> select the `kanglishbridge\extension` folder
4. Pin the KanglishBridge icon. The popup's dot turns green when the backend is ready.

### Try it
- **Popup:** type Kanglish, press *Translate* or Ctrl+Enter.
- **Any web page:** select text -> right-click -> *Translate Selected Text to English*.
- **WhatsApp Web** (`https://web.whatsapp.com/`): select text inside a message (or in the message box) -> click the small *Translate* button, or press **Alt+T**. With nothing selected, Alt+T translates only the draft you are typing. *Replace draft* edits the message box; **nothing is ever sent for you.** If WhatsApp blocks replacement, use *Copy*. If the button never appears, WhatsApp changed its markup: update `SELECTORS` in `extension/content/whatsapp.js`, or use the popup.

## 5. Datasets

| Column | Purpose |
|---|---|
| `source_romanized` | Kanglish as typed |
| `source_kn` | Same sentence in Kannada script (human verified) |
| `target_en` | Natural English reference |

`source_romanized + target_en` -> end-to-end evaluation; `source_romanized + source_kn` -> transliteration; `source_kn + target_en` -> MT. A `text,label` sentiment file is **not** a translation dataset (the validator says so).

```powershell
python scripts\validate_dataset.py ..\datasets\uploaded\mydata.csv
python scripts\prepare_dataset.py ..\datasets\uploaded\mydata.csv --out ..\datasets\uploaded\splits   # seed 42, leak-free
python scripts\evaluate.py --test ..\datasets\uploaded\splits\test.csv --out ..\results\run1 --ablation --make-human-template 30
```
Uploading a dataset never triggers training. Fine-tuning needs thousands of clean, human-verified pairs.

## 6. Evaluation outputs
`results.csv` (per row), `summary.json`, `comparison.csv/md` (with vs. without English protection), `metrics.png`, `error_analysis_worst15.csv`, optional `human_eval_template.csv`. Metrics: BLEU, chrF, chrF++, latency, English-token preservation (share of protected English words that appear in the output - a rough proxy), human adequacy/fluency (1-5).

## 7. Troubleshooting
| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv; reinstall the requirements file that mentions it |
| `/health` says `models_ready: false`, "error" | Read the backend console log: it prints the real exception. Usually a missing package or failed download |
| Model download fails | Check internet/proxy; retry (Hugging Face caches partial downloads). Corporate networks may block `huggingface.co` |
| `fairseq` / IndicXlit install fails | Use Python 3.10 and WSL2 (section 4) |
| IndicTrans2 errors about `use_cache` / remote code | Pin `transformers` to an older version in `requirements-models.txt` |
| CUDA errors / out of memory | `$env:KB_DEVICE="cpu"` (the 200M model runs on CPU, just slower). CUDA is used automatically only if available |
| Port 8000 busy | `netstat -ano \| findstr :8000`. Using another port means editing `BASE` in `extension/api.js` **and** `host_permissions` in `manifest.json`, then reloading the extension |
| Popup says "Backend offline" | Backend not running, firewall prompt dismissed, or WSL localhost forwarding disabled |
| Context menu does nothing | Restricted pages (`chrome://`, Web Store) cannot be scripted; try a normal site. Reload the extension after edits |
| `Extension context invalidated` | You reloaded the extension; refresh the web page |
| First translation very slow | First call warms up the model; later calls are faster |

## 8. Configuration (environment variables)
`KB_DEVICE` (auto/cpu/cuda), `KB_NUM_BEAMS`, `KB_PORT`, `KB_PROTECT_ENGLISH`, `KB_REQUEST_TIMEOUT_S`, `KB_MAX_TEXT_CHARS`, `KB_EXTENSION_ID` (lock CORS to your extension's ID), `KB_EXTRA_ENGLISH_WORDLIST` (path to a larger word list), `KB_SKIP_MODEL_LOAD=1` (UI work without models; translation returns 503).
