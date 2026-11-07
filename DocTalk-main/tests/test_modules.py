"""Every module's pack + scripted demo must be internally consistent (refs, quotes, ids)."""
import re

import pytest

from demo.backend import ScriptedBackend
from src.agents.summary import reading_grade
from src.modules import MODULES
from src.schemas import Flag


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip().lower()


@pytest.mark.parametrize("key", list(MODULES))
def test_module_loads_and_flags_resolve(key):
    m = MODULES[key]
    cl, chart, script, gc = m.checklist(), m.chart(), m.script(), m.gap_checks()
    assert m.profiles() and cl.items
    ids = {i.id for i in cl.items}
    turns = script["turns"]
    assert [t["idx"] for t in turns] == list(range(len(turns)))
    assert {t["speaker"] for t in turns} <= set(m.speakers)
    assert script["profile_id"] in m.profiles()
    for i, f in enumerate(gc["flags"]):
        flag = Flag.model_validate({"flag_id": f"f{i}", "visit_id": "v", "type": f["type"], "evidence": f["evidence"], "rationale": f["rationale"]})
        for e in flag.evidence:
            if e.source == "checklist":
                assert e.ref in ids, e.ref
            elif e.source == "chart":
                ent = chart.entry(e.ref)
                assert ent and _norm(e.quote) in _norm(ent.display)
            else:
                assert _norm(e.quote) in _norm(turns[int(e.ref)]["text"]), (key, e.ref, e.quote)
        if f["trigger_turn"] is not None:
            assert f["trigger_turn"] < len(turns)
    assert set(gc["coverage"]) <= ids
    assert all(v is None or v < len(turns) for v in gc["coverage"].values())


@pytest.mark.parametrize("key", ["onc_adult", "onc_peds"])
def test_oncology_items_are_honestly_unverified_and_summaries_readable(key):
    m = MODULES[key]
    assert all(i.verification_status == "UNVERIFIED" for i in m.checklist().items)  # no invented citations
    fp = m.flag_plan()
    assert reading_grade(fp["summary"]) <= 9
    if "child_summary" in fp:
        p = m.profiles()[m.script()["profile_id"]]
        assert p.child_present and reading_grade(fp["child_summary"]) <= p.child_summary_grade + 1.5


@pytest.mark.parametrize("key", list(MODULES))
def test_scripted_backend_runs_each_module(key):
    m = MODULES[key]
    be = ScriptedBackend(m.script()["visit_id"], m.chart(), m.checklist(), m.profiles()[m.script()["profile_id"]], gc=m.gap_checks(), plan=m.flag_plan())
    for t in m.script()["turns"]:
        be.add_turn(t["speaker"], t["text"])
    be.end_visit()
    assert be.flags and be.summary and be.clarify
    assert len(be.flags) == len(m.gap_checks()["flags"])


def test_prep_and_glossary_shape():
    for key in ("onc_adult", "onc_peds"):
        m = MODULES[key]
        assert m.prep()["groups"] and m.prep()["call_card"]
        assert all("plain" in v for v in m.glossary().values())
