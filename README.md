# hashdb

I wrote hashdb back in 2011 when I was drowning in duplicate emails spread
across a dozen maildir folders. I'd migrated between mail clients a few times,
and each migration left behind partial copies of everything. What I needed was
something dead simple: fingerprint every file, toss the fingerprints into a
database, and then use that database to nuke the duplicates.

hashdb walks a set of directories, computes an MD5 checksum for each file (or
extracts the `Message-Id` header for email), stores the results in a SQLite
database, and can then remove files whose checksums already appear in the
database. It uses multiprocessing to scan files in parallel, so it's reasonably
quick even on large directory trees.

## Usage

Build a checksum database from one or more directories:

```
hashdb add ~/Mail/archive ~/Mail/inbox
```

This creates a `.checksums` SQLite file in the current directory. Now remove
duplicates from another location:

```
hashdb rmdups ~/Mail/unsorted
```

Any file in `unsorted` whose checksum matches an entry in the database gets
deleted.

For email specifically, you can use `Message-Id` instead of file content:

```
hashdb -m add ~/Mail/archive
hashdb -m rmdups ~/Mail/unsorted
```

Use `-d` to specify a different database path, and `-v` for verbose output.

## Development

If you've got Nix installed:

```
nix develop
lefthook install
```

That gives you Python, pytest, ruff, hypothesis, and all the other tools you
need. The pre-commit hooks run formatting, linting, tests, coverage, and fuzz
tests in parallel.

To run just the tests:

```
PYTHONPATH=src python -m pytest tests/ -v
```

`nix flake check` runs every quality gate -- formatting, linting, unit tests,
coverage threshold, and fuzz testing.
