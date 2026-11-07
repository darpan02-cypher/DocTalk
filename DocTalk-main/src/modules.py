"""Condition modules. Each module = a pack (checklist, profiles, gap checks, prep, glossary) + a scripted demo visit.

Adding a condition = a new `packs/<key>/` folder, a `demo/<key>/` folder, and one entry below.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import Chart, Checklist, PatientProfile

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Module:
    key: str
    label: str  # shown in the module picker
    checklist_title: str  # panel title
    source_note: str  # one line under the checklist
    pack_dir: Path
    demo_dir: Path
    speakers: tuple[str, ...] = ("clinician", "patient")
    teach_back: tuple[str, ...] = ()

    # ---- loaders (all plain JSON, cheap) ----
    def _json(self, path: Path, default=None):
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            if default is not None:
                return default
            raise

    def checklist(self) -> Checklist:
        return Checklist.model_validate(self._json(self.pack_dir / "checklist.json"))

    def profiles(self) -> dict[str, PatientProfile]:
        files = sorted((self.pack_dir / "profiles").glob("*.json"))
        profs = [PatientProfile.model_validate(json.loads(f.read_text())) for f in files]
        return {p.profile_id: p for p in profs}

    def gap_checks(self) -> dict:
        return self._json(self.pack_dir / "gap_checks.json")

    def prep(self) -> dict:
        """Pre-visit question prep, who-to-call card. Empty dict if the pack has none."""
        return self._json(self.pack_dir / "prep.json", default={})

    def glossary(self) -> dict[str, dict]:
        """term -> {plain, aliases[]}. Curated, not generated."""
        return self._json(self.pack_dir / "glossary.json", default={})

    def script(self) -> dict:
        return self._json(self.demo_dir / "script.json")

    def chart(self) -> Chart:
        return Chart.model_validate(self._json(self.demo_dir / "chart.json"))

    def flag_plan(self) -> dict:
        return self._json(self.demo_dir / "flags.json")


MODULES: dict[str, Module] = {
    "chest_pain": Module(
        key="chest_pain",
        label="Chest pain (adult)",
        checklist_title="Chest-pain checklist coverage",
        source_note="2021 AHA/ACC chest pain guideline.",
        pack_dir=ROOT / "packs" / "chest_pain",
        demo_dir=ROOT / "demo",
        speakers=("clinician", "patient", "caregiver"),
        teach_back=("In your own words, when do you come back to the clinic?", "What will you do if the pain gets worse?"),
    ),
    "onc_adult": Module(
        key="onc_adult",
        label="Cancer: adult treatment plan",
        checklist_title="Cancer treatment-visit checklist",
        source_note="Draft topics from common oncology communication guidance. Not yet clinician-reviewed.",
        pack_dir=ROOT / "packs" / "onc_adult",
        demo_dir=ROOT / "demo" / "onc_adult",
        speakers=("clinician", "patient", "caregiver"),
        teach_back=("In your own words, what is the plan for your treatment?", "Who will you call if you feel unwell, and what number?"),
    ),
    "onc_peds": Module(
        key="onc_peds",
        label="Cancer: child with parent",
        checklist_title="Pediatric cancer visit checklist",
        source_note="Draft topics from common pediatric oncology family-communication guidance. Not yet clinician-reviewed.",
        pack_dir=ROOT / "packs" / "onc_peds",
        demo_dir=ROOT / "demo" / "onc_peds",
        speakers=("clinician", "caregiver", "child"),
        teach_back=("Parent: in your own words, what are the next steps?", "Parent: when would you call the care team, and who?"),
    ),
}
DEFAULT_MODULE = "chest_pain"
