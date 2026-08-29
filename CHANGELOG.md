# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.4.0] - 2026-08-31

Parity pass with the `lib_vtop` rust crate: features that existed there but not
here.

### Added
- `VtopClient(user_agent=...)` and a `user_agent` property. VTOP binds a session
  to the User-Agent that created it, so it is now fixed for the life of a client
  and pinned onto every request, even when a fetch function passes its own
  headers. `DEFAULT_USER_AGENT` is the fallback.
- `VtopClient.get_cookie()`, returning the session's cookies as a `Cookie`
  header value so something outside the client (an in-app VTOP WebView) can
  reuse the session. Raises `VtopSessionError` when not logged in.
- `VtopClient.is_authenticated`.
- `StudentProfileModel.registration_number`, filled from the value captured at
  login — VTOP's profile page never renders it.

### Fixed
- `get_semesters()` no longer returns an empty list for students without a
  timetable (freshers especially), which surfaced as "No semesters available"
  right after login. It now falls back from the timetable page to the marks and
  exam schedule pages, which render the full institutional semester list.
- Outing submit and delete no longer report success as an error. VTOP styles the
  pending "Waiting for Mentor's Approval" status in red inside the requests
  table, which the parser read as a failure.

### Changed
- **Breaking:** `parse_outing_response(html)` is now
  `parse_outing_response(html, page_reload_message)`. VTOP reloads the outing
  page instead of returning a confirmation, so the caller supplies the wording
  for the successful outcome ("applied ... waiting for approval" vs "deleted").

## [0.2.8] - 2025-06-19

### Changed
- Implement retry mechanism when failed to solve captcha.

---

## [0.2.7] - 2025-06-11

### Changed
- GradeHistoryModel will default to "N/A" if no values are found.

---

## [0.2.6] - 2025-06-11

### Changed
- Grade History to nullable/empty.

---

## [0.2.5] - 2025-06-01

### Added
- Add Pending payments retrieval
- Add Payment receipts retrieval

---

## [0.2.4] - 2025-06-01

### Added
- Support for custom login id's

### Changed
- Remove registration number validation for now

---

## [0.2.3] - 2025-05-31

### Added
- Add registration number validation
- Add dynamic timeslots and days for timetable

### Changed
- Mask sensitive user information in login logs

---

## [0.2.3] - 2025-05-27

### Changed
- Timetable parser to not include any global variables

---

## [0.2.0] - 2025-05-24

### Added
- Initial release: Attendance, Timetable, Exam Schedule, Profile, Weekend and General Outing
