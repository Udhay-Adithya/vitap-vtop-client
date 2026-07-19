# Recorded fixtures

Real VTOP responses, captured by `scripts/record_fixtures.py` and scrubbed of
personal data. `tests/test_parser_contracts.py` runs the parsers against them.

These are committed on purpose. They are what lets the parser tests run offline,
in CI, with no credentials and no network.

## Recording them

```bash
cp .env.example .env      # fill in VTOP_USERNAME and VTOP_PASSWORD
python scripts/record_fixtures.py
```

VTOP will usually ask for a login OTP; the script prompts for it.

## Before you commit new fixtures

The scrubber removes registration numbers, names, contact details, embedded
photographs, session tokens and application numbers. It is covered by
`tests/test_fixture_scrubbing.py`, but it works on patterns, and VTOP can put
personal data somewhere the patterns do not reach.

**Read the diff before pushing:**

```bash
git diff tests/fixtures/
grep -riE "your-name|your-reg-no|@vitapstudent" tests/fixtures/
```

If something identifying got through, add a rule to `_scrub` in
`scripts/record_fixtures.py` and a test for it, then re-record.

## When to re-record

When `pytest -m live` starts failing. That means VTOP changed shape, and these
snapshots are now describing a portal that no longer exists. Re-record, look at
what moved in the diff, then fix the parsers.

Fixtures going stale is not a problem to avoid; it is the signal the whole
setup is built around. The live tests tell you *when*, the fixture diff tells
you *what*.
