# Running FactoryFlow and LLM-DES-Modeling through OpenRouter

Both repositories under `dt-eval/` were calling LLM providers directly
(Gemini via the Google Generative AI SDK, ChatGPT via the OpenAI API). They
have been switched so that **every LLM call goes through OpenRouter** at

```
https://openrouter.ai/api/v1
```

The **model names themselves were NOT changed** — each repo still asks for the
same models it did before (see the model list per repo below). Only the
transport/endpoint changed.

| Repo | Before (direct provider) | After (OpenRouter) |
|---|---|---|
| `FactoryFlow/FactoryFlow_v2` | `langchain_google_genai.ChatGoogleGenerativeAI` + `GEMINI_API_KEY` | `langchain_openai.ChatOpenAI` + `OPENROUTER_API_KEY`, `base_url=https://openrouter.ai/api/v1` |
| `FactoryFlow/DataFITR4amg` | `langchain_google_genai.llms.GoogleGenerativeAI` + `GOOGLE_API_KEY` | `langchain_openai.ChatOpenAI` + `OPENROUTER_API_KEY` |
| `LLM-DES-Modeling` | `openai.OpenAI` client hitting `api.openai.com` + `OPENAI_API_KEY` | same client with `base_url=https://openrouter.ai/api/v1` + `OPENROUTER_API_KEY` |

---

## 1. Prerequisites

- An OpenRouter account and an API key: <https://openrouter.ai/keys>
  (keys look like `sk-or-v1-...`).
- Python 3.10+ (3.11 recommended; FactoryFlow's local venv is 3.13).
- Node.js 18+ only for LLM-DES-Modeling (renders Mermaid diagrams via `npx`).

Export the key in your shell (or put it in the `.env` file — see notes
below), e.g.:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Optional but recommended for OpenRouter dashboard attribution:

```bash
export HTTP_REFERER="http://localhost"
export X_TITLE="dt-eval"
```

---

## 2. FactoryFlow (repo 1)

FactoryFlow contains **two runnable apps**; both now use OpenRouter.

### 2a. FactoryFlow_v2 (current app — Streamlit)

```bash
cd /ssd/projects/dt-eval/FactoryFlow/FactoryFlow_v2

# create a venv (or reuse FactoryFlow/.venv) and install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # now includes langchain-openai (no langchain-google-genai)

# provide the key
export OPENROUTER_API_KEY="sk-or-v1-..."

# launch the app (must run from the app/ folder, the code uses relative imports)
cd app
streamlit run Description_to_model_generator.py
```

Open the printed URL (default <http://localhost:8501>), type a description of
a manufacturing system and press **Generate Model**.

Environment note: `app/IM/AMG_with_langgraph.py` calls `load_dotenv()`, so you
may place `OPENROUTER_API_KEY=...` in a `.env` file inside `app/` instead of
exporting it.

Model used by this app (set in `app/IM/AMG_with_langgraph.py`):

- `google/gemini-3.1-pro-preview` — the previously configured `gemini-3-pro-preview`
  was retired from the OpenRouter catalog (404); 3.1-pro-preview is the current
  Gemini 3 Pro-class model there.

### 2b. DataFITR4amg (older PoC — Streamlit)

```bash
cd /ssd/projects/dt-eval/FactoryFlow/DataFITR4amg

python -m venv .venv
source .venv/bin/activate

# DataFITR4amg has no requirements.txt of its own; at minimum the LLM parts need:
pip install streamlit langchain langchain-openai langchain-community python-dotenv \
            fastapi uvicorn langserve blockdiag pillow requests
# (plus the rest of its simulation/data-fitting stack it already uses)

export OPENROUTER_API_KEY="sk-or-v1-..."

streamlit run FactoryFlow.py
```

Models used (set in `DataFITR4amg/IM/AMG.py`):

- `gemini-2.5-pro-exp-03-25` — description validation (`validatedescriptionwithllm`)
- `gemini-2.5-flash-preview-05-20` — netlist generation (`askllm`)

---

## 3. LLM-DES-Modeling (repo 2)

```bash
cd /ssd/projects/dt-eval/LLM-DES-Modeling

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # openai>=1.40 already present

export OPENROUTER_API_KEY="sk-or-v1-..."

python main.py
```

The workflow is interactive (manual model edits / adaptation instructions).
Artifacts are written to `results/`. A CSV event log is expected at
`data/workingtest.csv` (default).

Models used by this repo (unchanged, set as defaults in the agent files;
`main.py` builds one OpenRouter-wired client that every agent receives):

| Agent | File | Model |
|---|---|---|
| ModelBuilder | `agents/builder.py` | `gpt-5.1` |
| Modeloptimizer | `agents/optimizer.py` | `gpt-4o` |
| Modeladaptor (JSON step) | `agents/adapter.py` | `gpt-4o` |
| Modeladaptor (code gen) | `agents/adapter.py` | `gpt-5-mini` |
| Evaluater | `agents/evaluator.py` | `gpt-5-mini` |
| CPD | `agents/cpdagent.py` | `gpt-5-mini` |
| Modelvisualizer | `agents/visualizer.py` | `gpt-5-mini` |

---

## 4. Important note about model names on OpenRouter

The model identifiers in the code are passed to OpenRouter **verbatim**. If a
request returns `404 model_not_found` (or `400`), that identifier is not
available on your OpenRouter account under that exact spelling. OpenRouter
catalog ids are usually provider-prefixed, e.g.:

- `gemini-3-pro-preview` → `google/gemini-3.1-pro-preview` (retired; 3.1 is the
  current catalog id)
- `gemini-2.5-pro-exp-03-25` → `google/gemini-2.5-pro-exp-03-25`
- `gemini-2.5-flash-preview-05-20` → `google/gemini-2.5-flash-preview-05-20`
- `gpt-4o` → `openai/gpt-4o`
- `gpt-5-mini` → `openai/gpt-5-mini`
- `gpt-5.1` → `openai/gpt-5.1`

Fixing this means editing the model string in the file listed above (or in
`main.py`/the single `ChatOpenAI(...)` / `OpenAI(...)` site per app) to the
provider-prefixed slug that your account has enabled — this does **not**
change which underlying model is used. You can check available models at
<https://openrouter.ai/models> or with:

```bash
curl -s https://openrouter.ai/api/v1/models | jq -r '.data[].id' | grep -i "gemini-3-pro\|gpt-5"
```

---

## 5. Verification

To confirm traffic goes to OpenRouter (and not a vendor endpoint):

- All `base_url` / `openai_api_base` values point to `https://openrouter.ai/api/v1`.
- No source file imports `langchain_google_genai`, `google.generativeai`, or
  reads `GOOGLE_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` anymore.
- Requests appear in your OpenRouter usage dashboard
  (<https://openrouter.ai/activity>) when the apps are used.
