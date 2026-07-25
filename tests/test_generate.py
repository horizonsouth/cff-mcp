from cff.core.generate import MANIFEST_PATH, generate
from cff.core.schema import load_spec


def test_generates_every_document(full_answers):
    files = generate(full_answers)
    for doc in load_spec().documents:
        assert doc.filename in files
    assert MANIFEST_PATH in files


def test_provenance_header_on_every_document(full_answers):
    files = generate(full_answers)
    for name, content in files.items():
        if name.endswith(".md"):
            assert content.lstrip().startswith("<!-- Generated with")


def test_every_layer_feeds_at_least_one_document():
    spec = load_spec()
    used = {lid for doc in spec.documents for lid in doc.layers}
    orphans = {l.id for l in spec.layers} - used
    assert not orphans, f"layers feeding nothing: {orphans}"


def test_survives_sparse_input():
    files = generate({"mission": "Do the thing properly."})
    assert files  # no exception, partial stack still writes
