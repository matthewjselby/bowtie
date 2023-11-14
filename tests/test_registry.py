"""
Test the proper population of a Bowtie schema registry.
"""

from bowtie._cli import bowtie_schemas_registry
from bowtie._commands import HOMEPAGE

_, REGISTRY = bowtie_schemas_registry()


def test_root_schema():
    canonical_url = str(HOMEPAGE / "schemas/io/")
    retrieved = REGISTRY.get_or_retrieve(canonical_url)
    assert retrieved.value.contents["$id"] == canonical_url


def test_nonempty():
    assert REGISTRY