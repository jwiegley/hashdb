"""Shared test fixtures for hashdb tests."""

import pytest


@pytest.fixture
def sample_dir(tmp_path):
    """Create a directory with test files."""
    (tmp_path / "file1.txt").write_text("hello world")
    (tmp_path / "file2.txt").write_text("goodbye world")
    (tmp_path / "file3.txt").write_text("hello world")  # duplicate of file1
    return tmp_path


@pytest.fixture
def email_dir(tmp_path):
    """Create a directory with test email files."""
    (tmp_path / "mail1.txt").write_text(
        "From: alice@example.com\n"
        "Message-Id: <abc@example.com>\n"
        "Subject: Test\n\nBody\n"
    )
    (tmp_path / "mail2.txt").write_text(
        "From: bob@example.com\n"
        "Message-Id: <def@example.com>\n"
        "Subject: Test 2\n\nBody 2\n"
    )
    (tmp_path / "mail3.txt").write_text(
        "From: carol@example.com\n"
        "Message-Id: <abc@example.com>\n"
        "Subject: Duplicate\n\nDuplicate body\n"
    )
    return tmp_path


@pytest.fixture
def db_path(tmp_path):
    """Return a path for a temporary database."""
    return str(tmp_path / "test.db")
