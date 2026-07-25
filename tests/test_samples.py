"""The worked example shown on the web page must itself pass the validator.

If a sample answer ever goes thin or vague, the demo would contradict the
framework it demonstrates. This locks that door.
"""

from cff.core.schema import load_spec
from cff.core.validate import validate


def sample_answers():
    spec = load_spec()
    return {
        layer.id: {f.id: f.sample for f in layer.fields}
        for layer in spec.layers
    }


def test_every_field_has_a_sample():
    spec = load_spec()
    missing = [
        f"{layer.id}.{f.id}"
        for layer in spec.layers
        for f in layer.fields
        if not f.sample
    ]
    assert not missing, f"fields without a sample answer: {missing}"


def test_sample_stack_validates_clean():
    findings = validate(sample_answers())
    assert findings == [], [f.as_dict() for f in findings]
