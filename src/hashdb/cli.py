"""Command-line interface for hashdb."""

import argparse
import hashlib
import multiprocessing
import os
import re
import sqlite3
import sys
from os.path import isfile, join


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="hashdb",
        description="File checksum database for duplicate detection",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Report activity verbosely",
    )
    parser.add_argument(
        "-m",
        "--msgid",
        action="store_true",
        default=False,
        help="Use Message-Id field instead of checksum",
    )
    parser.add_argument(
        "-d",
        "--database",
        default=".checksums",
        help="Checksum database file (default: .checksums)",
    )
    parser.add_argument(
        "command",
        choices=["add", "rmdups"],
        help="Command to execute",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["."],
        help="Directories to process",
    )
    return parser


def compute_checksum(path, use_msgid=False):
    """Compute a checksum for a file.

    Returns (checksum, path, is_mail) tuple, or None if the file
    cannot be read or no checksum can be determined.
    """
    if not isfile(path):
        return None

    try:
        if use_msgid:
            with open(path, errors="replace") as fd:
                for line in fd:
                    match = re.match(
                        r"message-id:\s*(<[^>]+>)", line, re.IGNORECASE
                    )
                    if match:
                        return (match.group(1), path, True)
            return None
        with open(path, "rb") as fd:
            m = hashlib.md5()
            m.update(fd.read())
            return (m.hexdigest(), path, False)
    except OSError:
        return None


def init_db(database):
    """Open (and optionally create) the checksums database.

    Returns (connection, cursor).
    """
    create_table = not isfile(database)
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    if create_table:
        cursor.execute(
            """CREATE TABLE checksums (
                checksum TEXT NOT NULL,
                path TEXT NOT NULL,
                is_mail INTEGER NOT NULL,
                PRIMARY KEY (checksum)
            )"""
        )
        conn.commit()
    return conn, cursor


def walk_files(directories):
    """Yield all file paths under the given directories."""
    for directory in directories:
        for root, _dirs, files in os.walk(directory):
            for name in files:
                yield join(root, name)


def update_database(database, directories, use_msgid=False, verbose=False):
    """Add checksums for all files in directories to the database."""
    print("Updating checksum database", file=sys.stderr)
    conn, cursor = init_db(database)

    try:
        count = 0
        with multiprocessing.Pool(min(32, os.cpu_count() or 1)) as pool:
            paths = list(walk_files(directories))
            results = pool.starmap(
                compute_checksum,
                [(p, use_msgid) for p in paths],
            )
            for result in results:
                if result is None:
                    continue
                checksum, path, ismail = result
                try:
                    cursor.execute(
                        "INSERT INTO checksums"
                        " (checksum, path, is_mail)"
                        " VALUES (?, ?, ?)",
                        (checksum, path, 1 if ismail else 0),
                    )
                except sqlite3.IntegrityError:
                    if verbose:
                        print(
                            f"Duplicate checksum for {path}",
                            file=sys.stderr,
                        )
                count += 1
                if count % 1000 == 0:
                    print(f"Scanned {count} entries...", file=sys.stderr)
                    conn.commit()

        print(f"Done scanning {count} entries.", file=sys.stderr)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def remove_duplicates(database, directories, use_msgid=False, verbose=False):
    """Remove files whose checksums already exist in the database."""
    conn, cursor = init_db(database)

    try:
        duplicates = []
        with multiprocessing.Pool(min(32, os.cpu_count() or 1)) as pool:
            paths = list(walk_files(directories))
            results = pool.starmap(
                compute_checksum,
                [(p, use_msgid) for p in paths],
            )
            count = 0
            for result in results:
                if result is None:
                    continue
                checksum, path, _ismail = result
                cursor.execute(
                    "SELECT checksum FROM checksums WHERE checksum=?",
                    (checksum,),
                )
                if cursor.fetchone() is not None:
                    duplicates.append(path)
                count += 1
                if count % 1000 == 0:
                    print(f"Scanned {count} entries...", file=sys.stderr)

        print(f"Removing {len(duplicates)} duplicates...", file=sys.stderr)
        for path in duplicates:
            if isfile(path):
                os.remove(path)
                if verbose:
                    print(f"Removed: {path}", file=sys.stderr)
        print("Done removing duplicates.", file=sys.stderr)
    finally:
        cursor.close()
        conn.close()


def main(argv=None):
    """Entry point for hashdb CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        update_database(
            args.database, args.directories, args.msgid, args.verbose
        )
    elif args.command == "rmdups":
        remove_duplicates(
            args.database, args.directories, args.msgid, args.verbose
        )


if __name__ == "__main__":
    main()
