# Testing

This library scrapes a portal that can change without warning. The test suite
is built around that rather than pretending otherwise.

## The three layers

| Layer | Runs | Needs | Answers |
|---|---|---|---|
| Parser logic | every commit | nothing | did *I* break the parser? |
| Parser contracts | every commit | recorded fixtures | does the parser still handle real markup? |
| Live contracts | on demand | credentials + a human | **did VTOP change?** |

The first two are fast, offline and deterministic. Only the third can tell you
the portal moved, and only it needs secrets.

```bash
pytest              # layers 1 and 2. no network, no credentials.
pytest -m live      # layer 3. hits real VTOP.
```

Live tests are deselected by default, so a plain `pytest` — and CI — never
touches the network or needs a password.

## Why fixtures do not go stale in a way that matters

A fixture is a snapshot of one student at one moment. It cannot tell you what
VTOP looks like today, and it is not trying to. It tells you whether a change
*you* made broke a parser that used to work.

That is why the contract tests assert on **shape, never values**:

```python
assert record.course_id                      # good: the field is still found
assert record.course_id == "AM_CSE1008_00200"  # bad: breaks on re-record
```

A test asserting the CGPA is 9.12 fails when the student passes another
semester. A test asserting the CGPA is present and not the `"N/A"` placeholder
keeps working forever, and still catches the parser silently falling back.

## The loop

```
live tests fail  ->  VTOP changed
      |
      v
re-record fixtures  ->  git diff shows what moved
      |
      v
fix parsers  ->  contract tests go green  ->  commit fixtures + fix together
```

Committing the new fixtures alongside the parser fix means the next person can
see exactly what VTOP did and why the parser looks the way it does.

## Running the live tests

```bash
cp .env.example .env    # fill in VTOP_USERNAME and VTOP_PASSWORD
pytest -m live
```

`.env` is gitignored. Credentials are read from the environment and never
written into a test file.

These cannot run unattended: VTOP OTP-gates the login and the suite prompts on
stdin. That is a real constraint, not an oversight — an unattended runner would
need a stored password, and repeated failed logins can lock a VTOP account. Run
them by hand on a cadence you choose, ideally before publishing a release.

Every live test is read only. None of them submit, delete, or upload anything.
The write paths (outing submit/delete, assignment upload) are deliberately left
to layers 1 and 2, because a passing test is not worth filing a real leave
request or overwriting a real submission.

## What is not covered

The write paths above, and the OTP flows themselves, which need a human. Those
are exercised against mocked HTTP in the parser layers, so their logic is
tested even though the round trip is not.
