from cff.core.generate import generate
from cff.core.validate import summarize, validate


def test_good_stack_has_no_gaps(full_answers):
    findings = validate(generate(full_answers))
    assert not [f for f in findings if f.severity == "gap"]


def test_empty_layer_reported_as_gap():
    findings = validate({"mission": {"statement": "Ship it."}})
    gaps = {f.layer for f in findings if f.severity == "gap"}
    assert "audience" in gaps


def test_vague_wording_flagged():
    findings = validate({"success_criteria": {"checks": "It should be useful and correct overall."}})
    assert any(f.layer == "success_criteria" and f.severity == "note" for f in findings)


def test_never_gates(full_answers):
    findings = validate({"mission": {"statement": "x"}})
    assert all(f.severity in {"note", "suggestion", "gap"} for f in findings)
    assert "None of this blocks you" in summarize(findings)
