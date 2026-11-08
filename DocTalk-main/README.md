# DocTalk - A Second Ear For Care

**AI scribes capture what was said. DocTalk catches what was missed.**

DocTalk is an accessibility-first, multi-agent AI prototype that identifies communication gaps in doctor-patient consultations, particularly for older adults with hearing loss and limited health literacy. It runs on pluggable condition modules, covering **Cardiology**, **Oncology** and **Pediatric Oncology**.

Built for **CrownHacks 2026**.

## The Problem

Every year, approximately **12 million Americans experience outpatient diagnostic errors**. Meanwhile, patients can forget 40-80% of medical information soon after receiving it.

Traditional AI medical scribes document conversations. But documentation alone cannot reveal everything that was **never asked, never answered, or never understood**.

## Our Solution

DocTalk analyzes consultations for four critical gaps:

| Gap | What DocTalk checks |
|---|---|
| **Missed Questions** | Uncovered questions from a module checklist (10-item AHA/ACC guideline-referenced checklist for chest pain) |
| **Unanswered Concerns** | Patient worries that were never addressed |
| **Chart Contradictions** | Conflicts between patient statements and medical records |
| **Comprehension Breakdowns** | Potential misunderstandings that were not clarified, including plans never confirmed through teach-back |

### Designed for Accessible Healthcare

- **Live transcription:** Speaker-labeled conversations.
- **Evidence-backed analysis:** AI-generated flags checked against transcript or chart evidence.
- **Minimal alert fatigue:** Quiet indicators during consultations and consolidated wrap-up checks.
- **Patient-friendly summaries:** Plain-language explanations with readability assessment.
- **Prepare for the visit:** A pre-visit question list and who-to-call card. It helps patients ask, and never gives medical advice.
- **Accessible interface:** Adjustable text, high-contrast options, and read-aloud support.

## Condition Modules

DocTalk is not a single chest-pain demo. Each specialty is a swappable pack, so the same agents run across every module with no engine changes.

| Module | Speakers | Checklist items | Notes |
|---|---|---|---|
| **Cardiology** (chest pain) | Clinician, patient, caregiver | 10 | 2021 AHA/ACC chest pain guideline |
| **Oncology** | Clinician, patient, caregiver | 9 | Glossary of plain-language terms, prep list |
| **Pediatric Oncology** | Clinician, caregiver, child | 8 | Tracks caregiver comprehension and the child's own concerns |

Adding a condition means adding a `packs/<key>/` folder (checklist, gap checks, glossary, patient profiles, prep list), a `demo/<key>/` folder (scripted visit and chart), and one entry in [src/modules.py](src/modules.py).

## How It Works

```text
Clinician + Patient / Caregiver / Child Conversation
            |
            v
Deepgram Speech-to-Text + Diarization
            |
            v
Python Visit Orchestrator  <--  Condition Module (checklist, gap checks, glossary, profiles)
            |
            v
Specialized AI Agents
 |-- Checklist Agent
 |-- Concern Agent
 |-- Chart Agent
 |-- Comprehension Agent
            |
            v
Evidence Verification
            |
            v
Clinician Review + Patient Summary
```

Our deterministic Python orchestrator manages specialized agents instead of relying on one large AI prompt, making the processing pipeline easier to test and audit.

## Tech Stack

| Layer | Technologies |
|---|---|
| Interface | Streamlit, static landing page |
| Backend | Python, Pydantic |
| Speech recognition | Deepgram |
| AI inference | Groq, with Gemini and Ollama fallback configurations |
| Multi-agent processing | Custom Python orchestration and specialized LLM agents |
| De-identification | Microsoft Presidio, spaCy |
| Readability | textstat |
| Synthetic evaluation | Python, pytest, synthetic clinical datasets |

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/darpan02-cypher/DocTalk.git
cd DocTalk
```

### 2. Set up the environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch the application

```bash
./run.sh
```

This opens the landing page at `http://localhost:8800`. Launch the console from there.

To jump straight to the Streamlit console, run:

```bash
streamlit run app2.py
```

### 4. Explore the demo

Pick a module (Cardiology, Oncology or Pediatric Oncology) in the console and use the scripted demo backend to explore synthetic consultations without an LLM API key.

For live AI processing, set `GROQ_API_KEY` (or `GEMINI_API_KEY`). See `.streamlit/secrets.toml.example` for hosted settings. For Deepgram microphone streaming, configure `DEEPGRAM_API_KEY`.

The live microphone WebSocket relay currently targets localhost and requires additional configuration for remote deployment.

## Testing and Evaluation

Install development dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m scripts.build_dataset
python -m scripts.build_eval_dataset
```

The repository includes 29 synthetic development fixtures and a separate evaluation dataset containing 9 development and 15 test consultations. Evaluation data covers the chest-pain module.

Our evaluation goals are:

- **>=80% precision and recall** for gap detection.
- **<=1 false positive per consultation.**
- **Evidence-backed findings** with traceable transcript or chart references.

These are **targets, not validated performance results**.

## What's Next?

- Improve real-time speaker diarization and role identification.
- Validate gap detection through independent evaluation and clinical review.
- Expand to more specialties and languages, with clinician-reviewed checklists for each.
- Strengthen accessible patient summaries and trusted-source retrieval.
- Explore secure clinical integration with FHIR and appropriate consent controls.

## Safety and Limitations

**DocTalk is a research and hackathon prototype, not a medical device.**

The project uses synthetic clinical scenarios only. It does not provide diagnoses or treatment recommendations, is not validated for clinical use, and makes no HIPAA-compliance claim.

The checklists have not been clinician-reviewed. The Oncology and Pediatric Oncology modules are drafts. Speech recognition and gap-detection errors remain possible.

## Documentation

- [Project Specification](SPEC.md)
- [Implementation Progress](PROGRESS.md)
- [Project Report](docs/PROJECT_REPORT.md)
- [Deployment and Stage Guide](docs/DEPLOY_AND_STAGE.md)
- [Live Role-Play Demo](demo/README.md)
- [Evaluation Dataset](data/eval/README.md)
- [Synthetic Dataset](data/synthetic/README.md)

---

**DocTalk - Because every patient deserves to be heard, understood, and informed.**
