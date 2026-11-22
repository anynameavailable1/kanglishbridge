# KanglishBridge AI Environment Setup

## Environment
- Ubuntu 22.04 through WSL2
- Python 3.10.12
- Python virtual environment
- CPU-based PyTorch inference

## AI Models

### IndicXlit
Purpose: Romanized Kannada to Kannada script.

Package: ai4bharat-transliteration
Dependency: Fairseq 0.12.2

### IndicTrans2
Purpose: Kannada to English translation.

Model:
ai4bharat/indictrans2-indic-en-dist-200M

Source language: kan_Knda
Target language: eng_Latn

## Installation notes

The Fairseq dependency required compatibility work.

1. Install Python development headers:
   sudo apt install python3.10-dev

2. Use pip 24.0 for legacy dependency metadata compatibility.

3. Install compatible NumPy and Cython versions.

4. Clone Fairseq:
   git clone --depth 1 https://github.com/pytorch/fairseq.git

5. Install Fairseq from source with build isolation disabled.

6. Compile the required Cython components using:
   MAX_JOBS=2 python build_cython_only.py build_ext --inplace

7. Install:
   pip install ai4bharat-transliteration

## Hugging Face Authentication

Authenticate using the Python huggingface_hub login API.

Never store access tokens in the repository.

## Starting the backend

Activate the virtual environment.

Then execute:

unset KB_SKIP_MODEL_LOAD
export KB_DEVICE=cpu

uvicorn app.main:app --host 127.0.0.1 --port 8000

Health endpoint:
http://127.0.0.1:8000/health

API documentation:
http://127.0.0.1:8000/docs

## Important

- Do not upload .venv.
- Do not upload downloaded model weights.
- Do not upload Hugging Face authentication tokens.
- Model downloads are stored locally.
