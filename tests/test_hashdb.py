"""Unit and integration tests for hashdb."""

import sqlite3

from hashdb.cli import (
    compute_checksum,
    create_parser,
    init_db,
    main,
    remove_duplicates,
    update_database,
    walk_files,
)


class TestComputeChecksum:
    def test_md5_checksum(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = compute_checksum(str(f))
        assert result is not None
        checksum, path, is_mail = result
        assert len(checksum) == 32
        assert path == str(f)
        assert is_mail is False

    def test_returns_none_for_nonexistent(self):
        result = compute_checksum("/nonexistent/path/file.txt")
        assert result is None

    def test_returns_none_for_directory(self, tmp_path):
        result = compute_checksum(str(tmp_path))
        assert result is None

    def test_same_content_same_checksum(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("same content")
        f2.write_text("same content")
        r1 = compute_checksum(str(f1))
        r2 = compute_checksum(str(f2))
        assert r1[0] == r2[0]

    def test_different_content_different_checksum(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("content a")
        f2.write_text("content b")
        r1 = compute_checksum(str(f1))
        r2 = compute_checksum(str(f2))
        assert r1[0] != r2[0]

    def test_msgid_extraction(self, tmp_path):
        f = tmp_path / "email.txt"
        f.write_text(
            "From: test\nMessage-Id: <abc@example.com>\nSubject: test\n"
        )
        result = compute_checksum(str(f), use_msgid=True)
        assert result is not None
        checksum, _path, is_mail = result
        assert checksum == "<abc@example.com>"
        assert is_mail is True

    def test_msgid_returns_none_when_missing(self, tmp_path):
        f = tmp_path / "no_msgid.txt"
        f.write_text("From: test\nSubject: no id\n")
        result = compute_checksum(str(f), use_msgid=True)
        assert result is None

    def test_binary_file(self, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        result = compute_checksum(str(f))
        assert result is not None
        assert len(result[0]) == 32


class TestInitDb:
    def test_creates_table(self, db_path):
        conn, cursor = init_db(db_path)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "checksums" in tables
        cursor.close()
        conn.close()

    def test_idempotent(self, db_path):
        conn1, cur1 = init_db(db_path)
        cur1.close()
        conn1.close()
        conn2, cur2 = init_db(db_path)
        cur2.execute("SELECT COUNT(*) FROM checksums")
        assert cur2.fetchone()[0] == 0
        cur2.close()
        conn2.close()


class TestWalkFiles:
    def test_walks_directory(self, sample_dir):
        paths = list(walk_files([str(sample_dir)]))
        assert len(paths) == 3

    def test_walks_multiple_directories(self, tmp_path):
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        (d1 / "f1.txt").write_text("one")
        (d2 / "f2.txt").write_text("two")
        paths = list(walk_files([str(d1), str(d2)]))
        assert len(paths) == 2

    def test_empty_directory(self, tmp_path):
        paths = list(walk_files([str(tmp_path)]))
        assert paths == []


class TestUpdateDatabase:
    def test_adds_entries(self, sample_dir, db_path):
        update_database(db_path, [str(sample_dir)])
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checksums")
        count = cursor.fetchone()[0]
        # file1 and file3 are duplicates; one insert will fail
        assert count >= 2
        cursor.close()
        conn.close()

    def test_msgid_mode(self, email_dir, db_path):
        update_database(db_path, [str(email_dir)], use_msgid=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checksums")
        count = cursor.fetchone()[0]
        # mail1 and mail3 share a Message-Id
        assert count >= 2
        cursor.close()
        conn.close()


class TestRemoveDuplicates:
    def test_removes_known_duplicates(self, tmp_path, db_path):
        originals = tmp_path / "originals"
        originals.mkdir()
        (originals / "orig.txt").write_text("hello world")
        update_database(db_path, [str(originals)])

        check_dir = tmp_path / "check"
        check_dir.mkdir()
        (check_dir / "dup.txt").write_text("hello world")
        (check_dir / "unique.txt").write_text("something unique")

        remove_duplicates(db_path, [str(check_dir)])

        assert not (check_dir / "dup.txt").exists()
        assert (check_dir / "unique.txt").exists()

    def test_no_removal_when_no_match(self, tmp_path, db_path):
        originals = tmp_path / "originals"
        originals.mkdir()
        (originals / "orig.txt").write_text("original content")
        update_database(db_path, [str(originals)])

        check_dir = tmp_path / "check"
        check_dir.mkdir()
        (check_dir / "new.txt").write_text("completely different")

        remove_duplicates(db_path, [str(check_dir)])

        assert (check_dir / "new.txt").exists()


class TestCreateParser:
    def test_add_command(self):
        parser = create_parser()
        args = parser.parse_args(["add", "/tmp"])
        assert args.command == "add"
        assert args.directories == ["/tmp"]

    def test_rmdups_command(self):
        parser = create_parser()
        args = parser.parse_args(["rmdups", "/tmp"])
        assert args.command == "rmdups"

    def test_defaults(self):
        parser = create_parser()
        args = parser.parse_args(["add"])
        assert args.verbose is False
        assert args.msgid is False
        assert args.database == ".checksums"
        assert args.directories == ["."]

    def test_all_flags(self):
        parser = create_parser()
        args = parser.parse_args(
            ["-v", "-m", "-d", "my.db", "add", "/a", "/b"]
        )
        assert args.verbose is True
        assert args.msgid is True
        assert args.database == "my.db"
        assert args.directories == ["/a", "/b"]


class TestMain:
    def test_add_creates_database(self, sample_dir, db_path):
        main(["--database", db_path, "add", str(sample_dir)])
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checksums")
        assert cursor.fetchone()[0] >= 2
        cursor.close()
        conn.close()
