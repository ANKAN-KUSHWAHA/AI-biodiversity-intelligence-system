# Darukaa.Earth

Darukaa.Earth is an AI biodiversity intelligence system for the Darukaa.Earth Hackathon. It behaves as an evidence-first environmental scientist: it combines site conditions, retrieves relevant scientific knowledge, and produces practical biodiversity guidance. It is not a general-purpose chatbot.

## What it does

- Accepts a required natural-language environmental question.
- Accepts optional validated JSON for structured site data.
- Uses ChromaDB and embeddings to retrieve relevant FAO, IPCC, and UNEP knowledge-base documents.
- Requires at least three environmental decision variables before making a site-specific recommendation.
- Asks focused follow-up questions instead of inventing missing site data.
- Remembers the active assessment goal and environmental information during the browser session.
- Gives specific actions, environmental connections, metrics to monitor, time horizon, confidence, and source links.
- Handles later questions as compact conversational follow-ups rather than repeating the entire report.

## Example

**Question**

> My soil organic carbon is 0.3%, rainfall is low, and I grow wheat as a monoculture in a semi-arid region. What should I do to improve biodiversity?

Darukaa.Earth connects low soil organic carbon, low rainfall, monoculture wheat, and semi-arid context. It retrieves relevant evidence and may recommend a diversified rotation using cover crops or suitable legumes, while clearly noting local water and management trade-offs.

## Architecture

```text
Streamlit interface
  ├─ Required text question
  ├─ Optional structured JSON
  └─ Session memory for site facts and the active goal
                 ↓
LangGraph workflow
  parse_input → check_missing_information → retrieve_knowledge
                                              ↓
                         reason_about_environment → generate response
                 ↓
ChromaDB vector search ← OpenAI embeddings ← knowledge/documents
                 ↓
Evidence-backed recommendation or context-aware follow-up
```

## Conversational behavior

### Missing information

For a site-specific request, the system needs at least three environmental drivers, such as soil organic carbon, rainfall, land use, crop, soil moisture, pH, temperature, region, or human impact.

For example:

> Biodiversity is declining on my land.

The system asks for soil organic carbon, rainfall pattern, and land use. If the user replies with only one item, it retains the original goal and asks only for what remains. It does not make up values.

### Follow-up questions

After a complete assessment, users can continue the same conversation, for example:

> What crop is best to grow?

The reply uses the original goal, the remembered site data, recent conversation, and fresh retrieved evidence. It appears as a compact assistant response instead of a second full report. Use **Start a new assessment** to clear the previous site context before analysing a different location.

## RAG and scientific grounding

The starter library in `knowledge/documents/` contains short, inspectable documents with original source metadata:

- FAO Global Soil Partnership — soil organic carbon
- FAO — sustainable soil management
- IPCC — Climate Change and Land
- FAO — agroforestry
- UNEP — pollinators
- FAO — forest and landscape restoration

Each Markdown document includes `title`, `organization`, `year`, `source_url`, and `topic`. `scripts/ingest.py` splits the documents, creates embeddings, and persists the chunks in `chroma_db/`. Retrieved chunks are passed directly to the LLM; the user sees only readable scientific source citations, not internal scoring or extraction details.

## Project structure

```text
.
├── app.py                    # Streamlit interface and session conversation memory
├── requirements.txt
├── .env.example
├── knowledge/documents/      # Starter scientific source documents
├── scripts/ingest.py         # Chunk, embed, and store documents in ChromaDB
├── src/
│   ├── graph.py              # LangGraph nodes and routing
│   ├── state.py              # Shared graph state
│   ├── models.py             # Pydantic response/data models
│   ├── reasoning.py          # Transparent fact extraction and missing-data rules
│   ├── retrieval.py          # ChromaDB retrieval and provenance
│   └── llm.py                # OpenAI client configuration
└── chroma_db/                # Local generated vector database (not committed)
```

## Local setup

Requires Python 3.10 or later and an OpenAI API key with access to chat and embedding models.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Build the local knowledge base, then start the app:

```powershell
python scripts/ingest.py
python -m streamlit run app.py
```

Open the local URL that Streamlit displays, usually `http://localhost:8501`.

## Input formats

### Required text question

```text
What should I change to improve biodiversity on this farm?
```

### Optional JSON context

```json
{
  "soil_organic_carbon": 0.3,
  "rainfall": "low",
  "crop": "wheat",
  "land_use": "monoculture",
  "region": "semi-arid",
  "latitude": 23.2,
  "longitude": 77.4
}
```

Supported fields: `soil_organic_carbon`, `soil_ph`, `soil_moisture`, `rainfall`, `land_use`, `crop`, `biodiversity_indicators`, `temperature`, `region`, `human_impact`, `latitude`, and `longitude`.

## Demo checklist

1. Run the first example above: confirm recommendation, environmental connections, monitoring items, confidence, and sources appear.
2. Ask `Biodiversity is declining on my land.`: confirm the app requests missing context rather than recommending an action.
3. Reply with `SOC is 0.3%, rainfall is low, and land use is monoculture wheat.`: confirm the original goal is retained and a full assessment is generated.
4. Ask `What crop is best to grow?`: confirm the answer is a concise contextual follow-up.
5. Paste invalid JSON: confirm the UI gives a useful validation message.

## Error handling

The interface handles empty questions, invalid JSON, missing API keys, an empty/unbuilt vector database, retrieval failures, and LLM/API failures with visible messages instead of uncaught crashes.

## Deploy on Render

This repository includes `render.yaml` for a Render web-service deployment. Render is recommended for this project because its build command runs `python scripts/ingest.py` before Streamlit starts. This creates the ChromaDB knowledge base from the source documents during every deployment.

1. Push this repository to GitHub. Do not upload `.env`.
2. In Render, select **New** → **Blueprint** and choose the repository. Render detects `render.yaml`.
3. Enter `OPENAI_API_KEY` as a secret environment variable before deploying.
4. Deploy. The included Blueprint explicitly selects Render's `free` web-service plan. Render installs the dependencies, generates `chroma_db/`, then starts Streamlit on its assigned port.
5. Test the generated `https://<service-name>.onrender.com` URL with a demo question.

No persistent disk is needed for this hackathon demo because the database is rebuilt from `knowledge/documents/` on every deployment. Keep the service awake before presenting if your chosen hosting plan sleeps after inactivity.

## Security and CI CD

- Never commit `.env`, `.streamlit/secrets.toml`, or an API key. `.gitignore` excludes them.
- `chroma_db/` is generated and intentionally not committed.
- The Render build command is the deployment automation for this prototype; no separate CI test pipeline is configured.


## Hackathon requirement mapping

| Requirement | Darukaa.Earth implementation |
| --- | --- |
| Knowledge system | ChromaDB, embeddings, source metadata, and a local scientific document library |
| Clarifying questions | LangGraph stops before advice when three environmental drivers are not available |
| Memory and context | Streamlit session state retains site facts, active goal, and recent conversational context |
| Multi-metric reasoning | Reasoning and recommendations explicitly connect at least three available environmental variables |
| Evidence-backed advice | Retrieved evidence is supplied to the LLM; citations show original organization, title, year, and URL |
| Input handling | Mandatory text input plus optional Pydantic-validated JSON and latitude/longitude |
| Output quality | Specific action, mechanism, connections, metrics, timing, confidence, monitoring plan, and citations |
