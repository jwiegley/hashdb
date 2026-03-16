"""Hypothesis property-based fuzz tests for hashdb."""

import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from hashdb.cli import compute_checksum


@given(content=st.binary())
@settings(max_examples=200)
def test_checksum_handles_any_binary(content):
    """compute_checksum should never crash on arbitrary binary content."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = compute_checksum(path)
        if result is not None:
            checksum, rpath, is_mail = result
            assert len(checksum) == 32
            assert rpath == path
            assert is_mail is False
    finally:
        os.unlink(path)


@given(content=st.text())
@settings(max_examples=200)
def test_msgid_handles_any_text(content):
    """Message-Id parsing should never crash on arbitrary text."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f:
        f.write(content)
        path = f.name
    try:
        result = compute_checksum(path, use_msgid=True)
        if result is not None:
            checksum, _path, is_mail = result
            assert checksum.startswith("<")
            assert is_mail is True
    finally:
        os.unlink(path)


@given(content=st.binary())
@settings(max_examples=100)
def test_checksum_deterministic(content):
    """Same content should always produce the same checksum."""
    with tempfile.NamedTemporaryFile(delete=False) as f1:
        f1.write(content)
        p1 = f1.name
    with tempfile.NamedTemporaryFile(delete=False) as f2:
        f2.write(content)
        p2 = f2.name
    try:
        r1 = compute_checksum(p1)
        r2 = compute_checksum(p2)
        if r1 is not None and r2 is not None:
            assert r1[0] == r2[0]
    finally:
        os.unlink(p1)
        os.unlink(p2)
