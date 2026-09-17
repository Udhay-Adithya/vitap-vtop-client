# vitap-vtop-client — working notes

An async Python client that scrapes the VIT-AP VTOP portal using a student's own
credentials. There is no API — every feature is HTML scraped out of a JSP/
Thymeleaf app that changes without warning.

Sibling projects: the Flutter app (`../vitap_student_app`) and its Rust crate
`lib_vtop` (`../vitap_student_app/rust`). The app talks to Rust, **not** to this
package; this package backs the Python API service. The two implementations are
kept feature-parallel, so a fix here usually belongs there too — see
[Relationship to the Rust crate](#relationship-to-the-rust-crate).

## Stack

- **Python 3.13 + httpx (async)**, `bs4` + `lxml` for parsing, `pydantic` models.
- **Poetry** for deps. `pytest` (+ `pytest-asyncio`, `asyncio_mode = "auto"`).
- Captcha is solved **locally** by a tiny bundled model
  (`resources/weights.json`, `utils/solve_captcha.py`) — no external service.
- Everything is `async`. There is no sync API.

## Architecture

Five layers. Adding a feature means touching each one, in this order:

| Layer | Where | Job |
|---|---|---|
| Constants | `constants.py` | Every URL path, grouped by feature with a `# Comment` header |
| Parser | `parsers/<feature>_parser.py` | Pure `str -> model`. No I/O, no httpx |
| Model | `<feature>/model/<feature>_model.py` | Pydantic models, snake_case fields |
| Fetch | `<feature>/<feature>.py` | Builds the request, calls the parser, maps errors |
| Client | `client.py` | Public method, handles login, passes credentials down |

```
vitap_vtop_client/
  client.py               # VtopClient — the only public entry point
  constants.py            # all URL paths
  ssl_config.py           # VTOP's broken TLS chain (see below)
  certs/                  # bundled Sectigo intermediate + why it exists
  parsers/                # one module per page, pure functions
  <feature>/              # attendance, marks, grade_view, outing, payments, ...
    <feature>.py          #   fetch functions
    model/                #   pydantic models
  utils/                  # csrf, captcha, otp detection, small helpers
  exceptions/             # one error type per feature + parsing/session errors
scripts/record_fixtures.py  # captures real HTML into tests/fixtures/
tests/                      # see TESTING.md
```

**Keep parsers pure.** A parser takes HTML and returns a model. It never makes a
request and never needs a client. That is what lets the whole test suite run
offline against recorded fixtures.

---

## Adding a VTOP feature: the discovery workflow

**Never guess VTOP's markup or endpoints — look at the actual page.** VTOP's HTML
does not match intuition, its own docs, or (increasingly) the Rust crate. Every
bug fixed in this repo came from reading a live response.

### Step 1 — Log in and dump the page

Use this package itself as the exploration tool. It already handles the captcha,
the session, CSRF and TLS, so you get an authenticated session in a few lines.
Put credentials in `.env` (gitignored; see `.env.example`) and run:

```python
import asyncio, os, time
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))   # run from the repo root
from bs4 import BeautifulSoup
from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopLoginOtpRequiredError
from vitap_vtop_client.constants import HEADERS

PAGE = "/vtop/examinations/StudentMarkView"   # the page you're investigating

async def main():
    c = VtopClient(os.environ["VTOP_USERNAME"], os.environ["VTOP_PASSWORD"])
    try:
        await c.login()
    except VtopLoginOtpRequiredError:
        await c.verify_login_otp(input("OTP: ").strip())

    s = await c._ensure_logged_in()          # reg no + post-login CSRF
    r = await c._client.post(                # the live httpx client
        PAGE,
        data={
            "verifyMenu": "true",
            "authorizedID": s.registration_number,
            "_csrf": s.post_login_csrf_token,
            "nocache": int(time.time() * 1000),
        },
        headers=HEADERS,
    )
    open("/tmp/page.html", "w").write(r.text)
    print(r.status_code, len(r.text), "bytes")

    soup = BeautifulSoup(r.text, "lxml")
    for sel in soup.find_all("select"):      # dropdowns = ids you'll need
        opts = [o.get("value", "") for o in sel.find_all("option") if o.get("value")]
        print("select", sel.get("name"), len(opts), opts[:5])
    for t in soup.find_all("table"):         # tables = the data
        rows = t.find_all("tr")
        print("table", t.get("id"), t.get("class"), len(rows), "rows")
        for row in rows[:3]:
            print("   ", [x.get_text(strip=True)[:20] for x in row.find_all(["td", "th"])])
    await c.close()

asyncio.run(main())
```

Most VTOP pages are opened with exactly that `verifyMenu / authorizedID / _csrf /
nocache` POST body. Start there.

### Step 2 — Find the real endpoint in the page's JS

The page you just loaded is usually only a **shell**. The data arrives from a
second endpoint that the page's inline JavaScript calls. Grep the dumped HTML:

```bash
grep -oE 'url\s*:\s*"[^"]+"' /tmp/page.html | sort -u     # ajax endpoints
grep -oE 'function [a-zA-Z]+\(' /tmp/page.html | sort -u  # handlers to read
```

Then read the handler body — it tells you the **method, the exact field names,
and how the response is used**. Two real examples:

- Grade view: `doStudentGradeView` (semester -> tiles) and
  `getGradeViewDetails` (courseId -> expanded detail).
- Outing submit: `success: function(response){ $("#main-section").html(response) }`
  — i.e. the response is the *whole page reloaded*, not a status message. This
  detail is why the outing parser cannot infer success from the HTML alone.

### Step 3 — Match the request shape

VTOP is inconsistent. Copy whatever the page's JS does:

| JS builds | Use in httpx | Example |
|---|---|---|
| `new FormData(form)` | `files={"k": (None, v)}` (multipart) | `doStudentGradeView`, DA upload |
| `"a=1&b=2"` string | `content=body` + `Content-Type: application/x-www-form-urlencoded` | `getGradeViewDetails` |
| plain object / default | `data={...}` (urlencoded) | most pages |

Always include `authorizedID` and `_csrf`. Many endpoints also want a cache
buster: `x` (an RFC-1123 UTC timestamp) or `nocache` (epoch millis). If the JS
sends it, send it.

Some endpoints are AJAX-only and refuse to answer without
`X-Requested-With: XMLHttpRequest` (both outing delete endpoints). If a request
returns a login page or empty body, check the headers the JS sets.

Some endpoints require a **priming request** first: VTOP rejects the digital
assignment upload unless `processDigitalAssignment` was posted for that class
first, and the course page will not answer its dropdown lookups until
`StudentCoursePage` has been opened. If a call works in the browser but not here,
look at what the page loaded *before* it.

### Step 4 — Write it, in order

1. **Constants** — add the paths under a new `# Feature URL` block.
2. **Model** — pydantic, snake_case, matching VTOP's own wording where sane.
3. **Parser** — pure function in `parsers/`, raising `VtopParsingError` on
   failure. Follow [parser rules](#parser-rules).
4. **Fetch** — in `<feature>/<feature>.py`. Mirror an existing module
   (`grade_view/grade_view.py` is a good, current template): try/except mapping
   `httpx.RequestError -> VtopConnectionError`, re-raising `VtopParsingError`
   untouched, everything else to the feature's error type.
5. **Client method** — in `client.py`: `await self._ensure_logged_in()`, then
   call the fetch function with `registration_number` + `post_login_csrf_token`.
6. **Tests** — a parser-logic test always; a fixture + contract test if you can
   record one (`python scripts/record_fixtures.py`).
7. **Docs** — the API reference is generated from docstrings, so a complete
   docstring *is* the reference; there is no separate file to update. Add a
   page under `docs/guide/` only when VTOP's behaviour needs explaining rather
   than the method's signature. Build with `sphinx-build -b html -W docs
   docs/_build/html`; CI builds with `-W`, so a broken reference fails.

---

## How requests work

- One `httpx.AsyncClient` per `VtopClient`, `base_url=VTOP_BASE_URL`,
  `follow_redirects=True`, cookies persisted on the client, custom SSL context.
- **CSRF**: a pre-login token is used to log in; a **different** post-login token
  comes from the content page and is what every data request needs. It lives on
  `LoggedInStudent.post_login_csrf_token`. Never reuse the pre-login one.
- **Session**: VTOP has no logout-on-idle signal you can rely on. If a response
  comes back as the login page, the session died — surface it as
  `VtopSessionError` rather than parsing garbage.
- All paths live in `constants.py`. Do not inline URL strings in feature code.

### Login and the OTP gate

VTOP demands an OTP after inactivity or from a new IP. Login is therefore
**explicit and two-step** — this is the single biggest API constraint:

```python
try:
    await client.login()
except VtopLoginOtpRequiredError:
    await client.verify_login_otp(otp)   # or client.resend_login_otp()
```

`_ensure_logged_in()` deliberately **refuses** to auto-retry while an OTP is
pending (`client.otp_pending`) — a silent retry would invalidate the OTP already
mailed to the student. Repeated failed logins can lock a VTOP account, so never
loop on login.

### TLS

VTOP's server omits the Sectigo intermediate CA from its chain. Browsers and
curl fetch it automatically; Python does not, so requests fail with
`CERTIFICATE_VERIFY_FAILED`. The client bundles that intermediate
(`certs/vitap_sectigo_intermediate.pem`) and builds an SSL context of
`certifi roots + intermediate` in `ssl_config.py`. Verification stays **on** —
never "fix" a TLS error with `verify=False`. If VTOP changes CA, follow
`vitap_vtop_client/certs/README.md`.

---

## Parser rules

Hard-won; each one is a bug that shipped.

- **Locate columns by header label, not index.** VTOP inserts columns. The
  payment receipts parser read `amount` from index 2 for months after VTOP moved
  it to 5 — it was showing the invoice number as the amount.
- **Every field except the key one is optional.** Absent inputs mean a page
  variant, not a crash. The general outing form has no `parentContactNumber`
  input at all; assuming it did made the whole submit throw before it sent.
- **A rendered control does not mean it is usable.** VTOP renders download links
  for assignments that were never submitted, and outing form pages outside their
  eligibility window. Gate on the *status text*, not the link's presence.
- **Header rows are not always `<th>`.** The attendance-detail table renders its
  header with `<td>` inside the same table body. Guard data rows with something
  positive, e.g. `if not serial.isdigit(): continue`.
- **Pick leaf tables when markup nests.** The grade-view detail response injects
  its stats and marks tables *inside a cell of* the outer grade table, so "first
  table containing X" matches the wrapper. Select tables with no nested table.
- **Colour is not semantics.** VTOP paints the pending outing status
  ("Waiting for Mentor's Approval") in red. Red means pending, not error.
- **Degrade, don't explode.** Missing optional data returns `""` / `None` /
  `[]`. Raise `VtopParsingError` only when the page is genuinely unrecognisable,
  and put the *reason* in the message ("the weekend form is only served Tue–Fri").
- **Keep VTOP's typos.** The receipt download really does take `receitNo`.
  Comment them so nobody "fixes" them.

---

## Testing

Three layers — full rationale in **`TESTING.md`**, read it before adding tests.

```bash
pytest            # layers 1 + 2: offline, no credentials, no network. CI runs this.
pytest -m live    # layer 3: hits real VTOP, needs .env, prompts for the OTP.
```

1. `tests/test_parser_logic.py` — hand-built markup, pins parser *rules*.
2. `tests/test_parser_contracts.py` — real recorded fixtures, asserts **shape,
   never values** (`assert record.course_id`, not `== "AM_CSE1008_00200"`), so
   re-recording never breaks them. Skips cleanly if a fixture is missing.
3. `tests/test_live_contract.py` — the only layer that can tell you VTOP
   changed. Read-only: nothing here submits, deletes, or uploads.

**Fixtures are recorded, not written:** `python scripts/record_fixtures.py`
captures real pages and scrubs registration/application numbers, name, email,
phone, photos and session tokens (guarded by `tests/test_fixture_scrubbing.py`).
Fixtures are committed, so **read the diff before pushing** — the scrubber works
on patterns and VTOP can put personal data somewhere new.

When `pytest -m live` fails: re-record fixtures, read the diff to see what VTOP
moved, fix the parser, commit fixture + fix together.

---

## Things that will bite you

- **The weekend outing form is only served Tue 00:00 – Fri 23:59.** Outside that
  window VTOP returns the page with no student fields at all. `parse_outing_form`
  raises a message naming the window; don't report it as a network error.
- **Semester dropdowns are not equivalent across pages.** Timetable and
  attendance list only the student's *own* semesters and are **empty for
  freshers**; marks / exam schedule / grade view render the full institutional
  list for anyone. Prefer the timetable list, fall back to marks.
- **Grades exist only after a semester ends.** `get_grade_view` returns `[]` for
  the current semester until results publish. That is normal, not an error.
- **Outing submit/delete return the whole page reloaded.** VTOP's success popups
  are commented out server-side, so the caller must supply the success wording.
- **Marks may be unpublished** and biometric may be genuinely empty for a day.
  Empty is a legitimate result; don't treat it as failure.
- **Never fetch aggressively.** Each call is a real request against a fragile
  university server, and login is captcha + possibly OTP gated. Fan-out (like
  digital assignments fetching per-course details) should be deliberate.

## Conventions

- **Commits:** conventional, lowercase, scoped where useful, no attribution.
  `fix(parsers): correct three parsers against live vtop layouts`
- **Versioning:** semver. Field renames and signature changes are **breaking** —
  bump minor pre-1.0 and add a `BREAKING CHANGE:` footer.
- **Docstrings** on every public function: what it does, `Args`, `Returns`,
  `Raises`. Comment *why* VTOP forces an oddity, not what the code does.
- Never commit credentials, fixtures with real PII, or `.env`.

## Relationship to the Rust crate

`lib_vtop` is the reference implementation and the app's actual data source, but
it is **not** authoritative when it disagrees with live VTOP — it has drifted
(its payment receipts parser had the same stale columns this one did). Order of
truth: **live VTOP > this client > the Rust crate.** When you fix a parser here
against a live response, check whether Rust needs the same fix; when you port a
feature from Rust, verify its assumptions against a live page first.
