# Clinical Risk Stratification — Triage NLP Engine

A production-ready, rules-based NLP pipeline for clinical triage. Converts free-text clinical notes and structured vital signs into a structured risk assessment (LOW / MEDIUM / HIGH / CRITICAL) with full reasoning trace — no private data, no ML training required.

---

## Architecture

```
 Input
 ┌────────────────────────────────────────────────────┐
 │  free-text clinical note  +  structured vitals     │
 └──────────────────────┬─────────────────────────────┘
                        │
            ┌───────────▼───────────┐
            │   TextCleaner         │  abbreviation expansion,
            │   (preprocessing)     │  whitespace normalisation
            └───────────┬───────────┘
                        │ cleaned text
            ┌───────────▼───────────┐
            │   spaCy EntityRuler   │  pattern-based NER
            │   (NER layer)         │  SYMPTOM / DIAGNOSIS /
            │                       │  SEVERITY_MODIFIER
            └───────────┬───────────┘
                        │ Doc with entities
            ┌───────────▼───────────┐
            │   Negation Detector   │  pre/post token window,
            │   (phrase_matcher)    │  scope-break detection
            └───────────┬───────────┘
                        │ AnnotatedEntity list
            ┌───────────▼───────────┐
            │   Severity Annotator  │  MILD / MODERATE / SEVERE
            │   (phrase_matcher)    │  via left/right context
            └───────────┬───────────┘
                        │              ┌────────────────────┐
            ┌───────────▼───────────┐  │  VitalsScorer      │
            │   Rules Engine        │◄─┤  (threshold table) │
            │   (entity scorer +    │  │  flagged fields +  │
            │    override checks)   │  │  point total       │
            └───────────┬───────────┘  └────────────────────┘
                        │
            ┌───────────▼───────────┐
            │   RiskAssessment      │  risk_level, combined_score,
            │   (structured output) │  entity contributions,
            │                       │  vitals flags, reasoning text
            └───────────────────────┘
```

---

## Quick Start

### Option A — Docker (recommended)

```bash
# Build and run
docker compose up --build

# The API will be available at http://localhost:8000
# Interactive UI: http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### Option B — Local development

**Prerequisites:** Python 3.11+

```bash
# 1. Clone / enter the project directory
cd Pilot-proposal-for-Triage-Rules-based-risk-model-

# 2. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the spaCy model
python -m spacy download en_core_web_sm

# 5. Install the package itself (so imports resolve correctly)
pip install -e .

# 6. Run the development server
uvicorn api.main:app --reload --port 8000
```

Or use Make (if available):
```bash
make dev
```

Visit http://localhost:8000 for the web UI or http://localhost:8000/docs for the interactive API docs.

---

## API Reference

### POST /assess

Analyse a clinical note and return a structured risk assessment.

**Request body** (`application/json`):

```json
{
  "note_text": "65 year old male presents with sudden onset severe chest pain radiating to the left arm, associated with diaphoresis and shortness of breath.",
  "vitals": {
    "heart_rate": 112,
    "systolic_bp": 88,
    "diastolic_bp": 58,
    "respiratory_rate": 22,
    "spo2": 94,
    "temperature": 37.2,
    "gcs": 15
  },
  "patient_id": "DEMO-001"
}
```

All `vitals` fields are optional. `patient_id` is optional. `vitals` itself can be omitted or null.

**Response** (`200 OK`):

```json
{
  "patient_id": "DEMO-001",
  "risk_level": "CRITICAL",
  "combined_score": 9.241,
  "entity_score": 10.35,
  "vitals_score": 6,
  "entity_contributions": [
    {
      "text": "chest pain",
      "label": "SYMPTOM",
      "is_negated": false,
      "severity": "SEVERE",
      "weight": 2.0,
      "score_contribution": 4.0
    }
  ],
  "vitals_flags": [
    {
      "field": "systolic_bp",
      "value": 88.0,
      "points": 1,
      "reason": "BP abnormal"
    }
  ],
  "override_triggered": false,
  "override_reason": null,
  "reasoning_text": "Risk assessed as CRITICAL (combined score: 9.24). Active entities: chest pain [SEVERE], diaphoresis [SEVERE], shortness of breath [MODERATE]. Vital sign flags: HR moderately abnormal, BP abnormal.",
  "processing_time_ms": 1.85
}
```

### GET /health

Returns API and model status.

```json
{"status": "ok", "model_loaded": true}
```

### GET /examples

Returns up to 10 synthetic example cases (from `data/synthetic/sample_notes.jsonl`) for demonstration purposes.

---

## Architecture Explanation

### Layer 1 — Text Preprocessing (`clinical_nlp/preprocessing/`)

`TextCleaner` normalises whitespace and expands common clinical abbreviations (e.g. `c/o` → `complains of`, `sob` → `shortness of breath`). Extend `ABBREVIATION_MAP` to add more expansions.

### Layer 2 — Named Entity Recognition (`clinical_nlp/ner/`)

`build_spacy_pipeline()` loads the spaCy model and attaches an `EntityRuler` with inline token-pattern rules for:
- `SYMPTOM` — 40+ clinical symptom patterns
- `DIAGNOSIS` — 25+ ICD-adjacent diagnosis patterns
- `SEVERITY_MODIFIER` — severity qualifiers (severe, moderate, mild, worsening, etc.)

No external pattern files are required; all rules are in `entity_ruler.py`.

### Layer 3 — Negation and Severity (`clinical_nlp/phrase_matcher/`)

`detect_negation()` applies a sliding token-window algorithm:
- Pre-entity window (default 5 tokens): checks for negation triggers (`no`, `denies`, `without`, `ruled out`, etc.)
- Post-entity window (default 3 tokens): checks for post-positioned negators
- Scope-break detection: commas, periods, and contrastive conjunctions terminate the negation scope
- Pseudo-negation guard: phrases like `no change` or `no improvement` do not negate the following entity

`annotate_severity()` links `SEVERE`/`MODERATE`/`MILD` qualifiers to each entity via a left/right context window and the `SEVERITY_MAP` lookup table.

### Layer 4 — Vitals Scoring (`clinical_nlp/vitals/`)

`score_vitals()` evaluates each provided vital sign against tiered thresholds in `VITAL_THRESHOLDS`. First-match-wins per field. Points: 1 (mild), 2 (moderate), 3 (severe/critical). Unmeasured vitals contribute 0 points.

### Layer 5 — Rules Engine (`clinical_nlp/rules_engine/`)

Three-phase assessment:

1. **Override checks** — hard rules that bypass numeric scoring:
   - CRITICAL override: entity text in `CRITICAL_OVERRIDE_ENTITIES` (cardiac arrest, respiratory failure, anaphylaxis, etc.)
   - CRITICAL override: SpO2 < 85% or GCS < 9
   - HIGH override: 3 or more entities with SEVERE severity

2. **Numeric scoring** — entity scores (base weight × severity multiplier × diagnosis boost) are aggregated via `max × 0.6 + sum × 0.4`. Combined score = `entity_score × 0.55 + vitals_points × 0.45`.

3. **Threshold mapping** — CRITICAL ≥ 8.0, HIGH ≥ 5.0, MEDIUM ≥ 2.0, LOW otherwise.

### Layer 6 — Orchestrator (`clinical_nlp/pipeline/`)

`ClinicalRiskOrchestrator.run()` wires all layers together. Instantiate once at startup and reuse across requests for maximum performance.

### Layer 7 — API (`api/`)

FastAPI application with three routes, lifespan-managed pipeline singleton, and optional static file serving for the frontend.

---

## Adding a Private Data Adapter

The `DataAdapter` abstract base class defines the interface for any data source:

```python
# clinical_nlp/adapters/base.py
class DataAdapter(ABC):
    def load_cases(self, source: str) -> list[ClinicalInput]: ...
    def stream_cases(self, source: str) -> Iterator[ClinicalInput]: ...
    def validate_schema(self, raw_record: dict) -> ClinicalInput: ...
```

**Step-by-step to add a new adapter (e.g. MIMIC-III):**

1. Create `clinical_nlp/adapters/mimic.py`:

```python
from .base import DataAdapter
from clinical_nlp.schemas.input import ClinicalInput, VitalSigns
from typing import Iterator

class MimicDataAdapter(DataAdapter):
    def load_cases(self, source: str) -> list[ClinicalInput]:
        return list(self.stream_cases(source))

    def stream_cases(self, source: str) -> Iterator[ClinicalInput]:
        # Connect to MIMIC database / read deidentified export
        # yield self.validate_schema(raw_row) for each row
        ...

    def validate_schema(self, raw: dict) -> ClinicalInput:
        return ClinicalInput(
            note_text=raw["text"],
            vitals=VitalSigns(
                heart_rate=raw.get("heart_rate"),
                systolic_bp=raw.get("sbp"),
                # ... map remaining fields
            ),
            patient_id=str(raw.get("hadm_id")),
        )
```

2. Register it in `clinical_nlp/adapters/__init__.py`:

```python
from .mimic import MimicDataAdapter

ADAPTER_REGISTRY = {
    "synthetic": SyntheticDataAdapter,
    "mimic": MimicDataAdapter,
}
```

3. Set the environment variable to switch adapters:

```bash
export RISK_ENGINE_DATA_ADAPTER=mimic
export RISK_ENGINE_SYNTHETIC_DATA_PATH=/path/to/mimic/export
```

No changes to the core pipeline are needed.

---

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
coverage run -m pytest
coverage report -m

# Run specific test suites
pytest tests/unit/           # unit tests only
pytest tests/integration/    # integration tests only
pytest tests/api/            # API endpoint tests only
```

---

## Configuration

All settings are in `clinical_nlp/config.py` and can be overridden via environment variables prefixed with `RISK_ENGINE_`:

| Environment Variable              | Default                            | Description                              |
|-----------------------------------|------------------------------------|------------------------------------------|
| `RISK_ENGINE_SPACY_MODEL`         | `en_core_web_sm`                   | spaCy model name                         |
| `RISK_ENGINE_NEGATION_PRE_WINDOW` | `5`                                | Tokens to look back for negation         |
| `RISK_ENGINE_NEGATION_POST_WINDOW`| `3`                                | Tokens to look ahead for negation        |
| `RISK_ENGINE_SEVERITY_WINDOW`     | `3`                                | Context window for severity annotation   |
| `RISK_ENGINE_ENTITY_WEIGHT`       | `0.55`                             | Weight of entity score in combined score |
| `RISK_ENGINE_VITALS_WEIGHT`       | `0.45`                             | Weight of vitals score in combined score |
| `RISK_ENGINE_DATA_ADAPTER`        | `synthetic`                        | Adapter to use for /examples endpoint    |
| `RISK_ENGINE_SYNTHETIC_DATA_PATH` | `data/synthetic/sample_notes.jsonl`| Path to the synthetic JSONL dataset      |

Example (Docker):
```bash
docker run -e RISK_ENGINE_ENTITY_WEIGHT=0.6 -e RISK_ENGINE_VITALS_WEIGHT=0.4 -p 8000:8000 clinical-risk-engine
```

---

## Limitations and Known Caveats

1. **Negation scope is sentence-local.** The sliding window does not cross sentence boundaries. Complex multi-sentence negations (e.g. "History negative. No chest pain. No dyspnea.") are handled per sentence, which is the expected clinical behaviour, but very long sentences may cause issues.

2. **No coreference resolution.** "Patient has chest pain. It is severe." — the severity in the second sentence is not linked to the entity in the first. Severity annotation is context-window-only.

3. **Abbreviation expansion may produce false positives.** The regex-based expander (`cp` → `chest pain`) can mis-fire in uncommon contexts. Review `ABBREVIATION_MAP` for your specific corpus.

4. **Entity weights are heuristic.** `ENTITY_WEIGHTS` and score thresholds (`RISK_THRESHOLDS`) were designed for general clinical triage. They are not calibrated against any labelled dataset. Recalibrate for your specific patient population and clinical context before any real-world use.

5. **No ML model, no probabilistic output.** This is a deterministic rules engine. It does not produce confidence intervals or learn from feedback. It is intentionally interpretable and auditable.

6. **Vitals thresholds are generic.** The `VITAL_THRESHOLDS` table uses commonly cited abnormal ranges but does not account for age, sex, or chronic conditions (e.g. a baseline bradycardia in an athlete).

7. **Synthetic data only.** The included dataset (`data/synthetic/sample_notes.jsonl`) contains 20 fully synthetic notes. No real patient data is present or required.

8. **Not a medical device.** This software is for research and demonstration purposes only. It must not be used to make clinical decisions without appropriate validation, regulatory approval, and clinical oversight.

---

## Project Structure

```
.
├── api/
│   ├── main.py                  # FastAPI app, lifespan, route registration
│   ├── dependencies.py          # Dependency injection helpers
│   └── routes/
│       ├── assess.py            # POST /assess
│       ├── health.py            # GET /health
│       └── examples.py          # GET /examples
├── clinical_nlp/
│   ├── config.py                # Settings (pydantic-settings)
│   ├── adapters/                # DataAdapter interface + SyntheticDataAdapter
│   ├── ner/                     # spaCy EntityRuler pipeline builder
│   ├── phrase_matcher/          # Negation + severity annotators
│   ├── pipeline/                # Orchestrator (main entry point)
│   ├── preprocessing/           # TextCleaner
│   ├── rules_engine/            # Entity scorer + rules engine
│   ├── schemas/                 # Pydantic I/O models
│   └── vitals/                  # VitalsScorer + threshold table
├── data/
│   └── synthetic/
│       └── sample_notes.jsonl   # 20 synthetic clinical cases
├── frontend/
│   ├── index.html               # Single-page UI
│   └── static/
│       ├── app.js               # Vanilla JS frontend logic
│       └── style.css            # Styles + responsive layout
├── tests/
│   ├── conftest.py
│   ├── api/                     # FastAPI endpoint tests (httpx AsyncClient)
│   ├── integration/             # End-to-end pipeline + adapter tests
│   └── unit/                    # Unit tests for each component
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```
