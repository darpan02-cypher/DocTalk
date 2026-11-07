"""Backends for the live demo. Both expose the same small interface used by app.py.

ScriptedBackend: hardcoded. Each spoken line is matched to the prepared script by text similarity; flags and
checklist ticks come from packs/chest_pain/gap_checks.json. Safe on stage (no network), but it only reacts to scripted lines.
EngineBackend: the real engine (process_turn / finalize / SummaryAgent) on a DEMO (cache) or LIVE LLM client.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.pack import load_gap_checks
from src.schemas import Chart, Checklist, Flag, GapType, PatientProfile, PlanItem, Turn

DEMO_DIR = Path(__file__).resolve().parent


def load_script() -> dict:
    return json.loads((DEMO_DIR / "script.json").read_text())


def load_chart() -> Chart:
    return Chart.model_validate(json.loads((DEMO_DIR / "chart.json").read_text()))


def load_flag_plan() -> dict:
    return json.loads((DEMO_DIR / "flags.json").read_text())


@dataclass
class Backend:
    visit_id: str
    chart: Chart
    checklist: Checklist
    profile: PatientProfile
    turns: list[Turn] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    coverage: dict[str, int | None] = field(default_factory=dict)
    off_script: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ended: bool = False
    summary: str = ""
    summary_grade: float | None = None
    clarify: list[str] = field(default_factory=list)

    def add_turn(self, speaker: str, text: str) -> Turn:  # pragma: no cover - interface
        raise NotImplementedError

    def end_visit(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    @staticmethod
    def _words(s: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'").replace("'", ""))

    def _anchor(self, quote: str | None, fallback: int) -> int:
        """Turn that actually contains the quote (speech-to-text splits and rewords lines, so script indices drift).

        Falls back to the scripted index, clamped to a turn that exists."""
        q = self._words(quote or "")
        best, best_r = None, 0.0
        for t in self.turns:
            tw = set(self._words(t.text))
            r = sum(w in tw for w in q) / len(q) if q else 0.0
            if r > best_r:
                best, best_r = t.idx, r
        if best is not None and best_r >= 0.75:
            return best
        return min(fallback, max(len(self.turns) - 1, 0))

    def _gap_flag(self, i: int, f: dict, at: int) -> Flag:
        ev = []
        for e in f["evidence"]:
            e = dict(e)
            if e["source"] == "transcript":
                e["ref"] = str(self._anchor(e.get("quote"), int(e["ref"])))
            ev.append(e)
        return Flag.model_validate(
            {"flag_id": f"gap-{i}", "visit_id": self.visit_id, "type": f["type"], "evidence": ev,
             "rationale": f["rationale"], "verified": True, "raised_at_turn": at}
        )

    def apply_live_gap_checks(self) -> None:
        """Hardcoded live checks (chart contradiction, comprehension breakdown, checklist ticks).

        A flag with trigger_turn N shows once N+1 turns exist, whatever was said. Its transcript evidence is anchored to the turn whose text matches the quote.
        Omission checks (missed question, unanswered concern) wait for End visit.
        """
        gc, n = load_gap_checks(), len(self.turns)
        dismissed = {f.flag_id for f in self.flags if f.dismissed}
        # rebuilt every turn so each flag re-anchors to the real turn once the line is actually spoken
        self.flags = [
            self._gap_flag(i, f, n - 1).model_copy(update={"dismissed": f"gap-{i}" in dismissed})
            for i, f in enumerate(gc["flags"])
            if f["trigger_turn"] is not None and n > f["trigger_turn"]
        ]
        self.coverage = {k: v for k, v in gc["coverage"].items() if n > v}

    def apply_gap_checks(self) -> None:
        """Replace flags, coverage and clarify prompts with the chest-pack's hardcoded gap-check output."""
        gc = load_gap_checks()
        self.flags = [self._gap_flag(i, f, max(len(self.turns) - 1, 0)) for i, f in enumerate(gc["flags"])]
        self.coverage = dict(gc["coverage"])
        self.clarify = list(gc["clarify"])

    def dismiss(self, flag_id: str) -> None:
        self.flags = [f.model_copy(update={"dismissed": True}) if f.flag_id == flag_id else f for f in self.flags]


class ScriptedBackend(Backend):
    """Gap checks are hardcoded (packs/chest_pain/gap_checks.json) and independent of the spoken text."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.plan = load_flag_plan()

    def add_turn(self, speaker: str, text: str) -> Turn:
        turn = Turn(idx=len(self.turns), speaker=speaker, text=text.strip())
        self.turns.append(turn)
        self.apply_live_gap_checks()
        return turn

    def end_visit(self) -> None:
        self.apply_gap_checks()
        self.summary = self.plan["summary"]
        self.ended = True
        self._grade()

    def _grade(self) -> None:
        try:
            from src.agents.summary import reading_grade

            self.summary_grade = round(reading_grade(self.summary), 2)
        except Exception:  # textstat missing
            self.summary_grade = None


class EngineBackend(Backend):
    """Real engine. DEMO mode only works for texts already in data/llm_cache or demo/cache."""

    def __init__(self, *a, llm=None, plan_items: list[PlanItem] | None = None, **kw):
        super().__init__(*a, **kw)
        from src import engine

        self.engine = engine
        self.llm = llm
        self.plan_items = plan_items or []
        self.state = engine.new_state(self.visit_id, self.profile)
        
    def add_turn(self, speaker: str, text: str) -> Turn:
        turn = Turn(idx=len(self.state.turns_seen), speaker=speaker, text=text.strip())
        self.state = self.engine.process_turn(self.state, turn)  # records only: no model calls, gap checks are hardcoded
        self.turns = list(self.state.turns_seen)
        self.apply_live_gap_checks()
        return turn

    def end_visit(self) -> None:
        from src.agents.summary import SummaryAgent
        from src.schemas import Transcript

        self.apply_gap_checks()
        tr = Transcript(visit_id=self.visit_id, chart_id=self.chart.chart_id, turns=self.state.turns_seen)
        try:
            res = SummaryAgent(self.llm).run(tr, self.flags, self.plan_items, self.profile)
            self.summary, self.summary_grade = res.text, res.grade
        except Exception as e:  # LLMError or missing textstat: show, do not crash the demo
            self.errors.append(f"summary: {type(e).__name__}")
        self.ended = True
