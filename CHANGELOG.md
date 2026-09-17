# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.5.1] - 2026-09-17

### Fixed
- `VtopExamScheduleError`, `VtopMarksError`, `VtopGeneralOutingError` and
  `VtopWeekendOutingError` are now exported from `vitap_vtop_client.exceptions`.
  They were defined and raised but never re-exported, so callers could not name
  them and had to fall back to the `VitapVtopClientError` base.
- The marks module wrapped unexpected failures in `VtopAttendanceError`, so a
  marks failure reached callers as an attendance one and `VtopMarksError` was
  never raised despite being defined for it. Catching `VtopAttendanceError`
  around `get_marks` no longer works; catch `VtopMarksError` instead.

## [0.5.0] - 2026-08-31

### Added
- `get_capstone_attendance(sem_sub_id)` for the capstone/SDP attendance VTOP
  added to the attendance page. Kept separate from `get_attendance` because it
  is per semester rather than per course and counts present / on duty / absent;
  returns `None` for students without a capstone. Verified against a live
  response.
- The academic calendar: `get_calendar_class_groups`, `get_calendar_months`,
  `get_calendar_month`, and `get_academic_calendar`, which walks all of a
  semester's months and returns one flat, date-ordered list of days with their
  events (including named holidays).
- `VtopCalendarError`.

## [0.4.0] - 2026-08-29

Parity pass with the `lib_vtop` rust crate: features that existed there but not
here, plus the fixes that running against live VTOP surfaced.

### Added
- Faculty: `search_faculty`, `get_all_faculty` (VTOP serves the whole directory
  from the search endpoint when `empId` is empty) and `get_faculty_details`,
  which returns the profile and weekly office hours.
- Digital assignments: `get_digital_assignments` fans out one request per
  course because VTOP serves the course list and the per course assignments
  from separate endpoints; `get_course_assignments` fetches a single course;
  `download_assignment_file` retrieves question papers and submitted files;
  `upload_assignment` submits a file and `verify_assignment_upload_otp`
  confirms it when VTOP holds the upload for an emailed OTP. Uploads are
  validated before hitting the network: non empty, one of pdf, doc, docx, xls
  or xlsx, and at most 4MB.
- The course page: `init_course_page` (VTOP requires it before it will answer
  the lookups), `get_course_page_courses`, `get_course_page_slots`,
  `get_course_detail`, `download_course_material` and `download_course_plan`.
- `get_grade_view(sem_sub_id)` and `get_grade_view_detail(sem_sub_id,
  course_id)` for the StudentGradeView page, which neither this client nor the
  rust crate covered. The detail carries per-component marks, the total, and
  class statistics including the grade cutoff ranges.
- `get_attendance_detail`, the per-class register behind each attendance row.
- Outing writes: `submit_general_outing` and `submit_weekend_outing` are now
  reachable on the client (the functions existed but were never exposed),
  alongside `delete_general_outing`, `delete_weekend_outing`,
  `download_general_outing_pass` and `download_weekend_outing_form`.
- `download_payment_receipt`, keeping VTOP's misspelled `receitNo` query
  parameter as the server expects it.
- `GradeCourseHistoryModel` and `GradeHistoryModel.courses`. Only the CGPA
  summary was parsed before, so the entire per course grade table was lost.
- `BiometricModel.serial` and `.date`, which the parser was discarding, plus
  the `day`, `out_time` and `duration` placeholders the rust crate carries.
- `AttendanceModel.faculty`, `.course_type_code` and a real `.course_id`, all
  read from the `callStudentAttendanceDetailDisplay` onclick on each row.
- `serial` and `can_download` on both outing records. `can_download` reflects
  whether VTOP actually offers the file: a download link for general outings,
  an accepted status for weekend outings, which render the link regardless.
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
- `VtopDigitalAssignmentError` and its file, size, type and upload OTP
  subclasses.
- A three layer test suite: parser logic over hand built markup, parser
  contracts over recorded fixtures, and a live layer that is deselected by
  default because VTOP's login OTP means it cannot run unattended.
  `scripts/record_fixtures.py` captures fixtures and scrubs registration and
  application numbers, names, contact details, photographs and session tokens
  before writing, since fixtures are committed.

### Fixed
- VTOP omits the Sectigo intermediate CA from its TLS chain. Browsers and curl
  fetch it automatically over AIA; Python's `ssl` does not, so every request
  failed with `CERTIFICATE_VERIFY_FAILED` unless the caller set `SSL_CERT_FILE`
  by hand. The intermediate now ships as package data and the client verifies
  against certifi's roots plus that certificate. Verification stays fully
  enabled; nothing is bypassed.
- `get_semesters()` no longer returns an empty list for students without a
  timetable (freshers especially), which surfaced as "No semesters available"
  right after login. It now falls back from the timetable page to the marks and
  exam schedule pages, which render the full institutional semester list.
- Outing submit and delete no longer report success as an error. VTOP styles the
  pending "Waiting for Mentor's Approval" status in red inside the requests
  table, which the parser read as a failure.
- The general outing submit crashed before it even sent, because
  `parse_outing_form` subscripted a `parentContactNumber` input the general form
  does not render. Every field except the registration number is now optional;
  a missing registration number means the form did not render at all, which
  raises a clear error naming the weekend eligibility window.
- The weekend outing parser assumed 13 columns and crashed on the live 11
  column table, which carries the booking id only inside the download link. It
  now handles both the 11 and 14 column forms.
- The payment receipts parser raised after VTOP inserted invoice and fee
  columns, shifting the amount and the view button. Columns are now located by
  header label and the button by its handler, skipping rows without one.
- The attendance detail parser read VTOP's header row as data, because it is
  rendered with `td` cells inside the same table. Rows must now lead with a
  numeric serial.
- Attendance tolerates the "attendance between" column being absent, which
  previously shifted `debar_status` onto the wrong cell.
- The grade history summary table is selected by looking for the one containing
  CGPA rather than taking the first table matching the class, which could pick
  the wrong one.

### Changed
- **Breaking:** `AttendanceModel.course_id` now holds the course id rather than
  the class number, so it can be used to request detail. The class number moved
  to `class_number`, and `within_attendance_percentage` is now
  `attendance_between_percentage`.
- **Breaking:** `ExamEntry.course_title`, `.type`, `.registration_number`,
  `.date` and `.session` are now `.course_name`, `.course_type`, `.course_id`,
  `.exam_date` and `.exam_session`. The fifth column was labelled
  `registration_number` but has always held the course id.
- **Breaking:** `BiometricModel.time` is now `in_time`.
- **Breaking:** `GeneralOutingRequest.leave_id` is `""` instead of the `"N/A"`
  sentinel when no leave pass is available.
- **Breaking:** `parse_outing_response(html)` is now
  `parse_outing_response(html, page_reload_message)`. VTOP reloads the outing
  page instead of returning a confirmation, so the caller supplies the wording
  for the successful outcome ("applied ... waiting for approval" vs "deleted").
  Both submit paths now use it in place of `find_outing_response`, which matched
  one exact inline style string.

## [0.3.0] - 2026-07-19

### Added
- The login OTP flow. VTOP gates login behind an OTP after inactivity or when
  signing in from a new IP address, which the client had no support for, so
  logins against current VTOP could not complete. `VtopClient.login()` now
  raises `VtopLoginOtpRequiredError` carrying the OTP page's CSRF token;
  `verify_login_otp(otp)` and `resend_login_otp()` finish the login, and
  `otp_pending` reports whether one is outstanding.
- `VtopLoginOtpRequiredError`, `VtopLoginOtpIncorrectError` and
  `VtopLoginOtpExpiredError`.
- `get_semesters()`, which parses the `semesterSubId` select on the timetable
  page, skipping the placeholder option and stripping the "- AMR" suffix.

### Fixed
- Login error handling matches on the response URL as a substring rather than by
  exact equality, aligning with the rust crate.
- `find_registration_number` was being handed the response object instead of its
  text.

### Changed
- **Breaking:** login is now explicit. Callers must handle
  `VtopLoginOtpRequiredError` and call `verify_login_otp`. `_ensure_logged_in`
  refuses to silently retry while an OTP is pending, since a retry would
  invalidate the OTP already sent.
- **Breaking:** the `SemSubID` dictionary is removed from constants. It had to
  be edited by hand for every new semester and was already stale, and a stale
  entry silently resolves to the wrong semester rather than failing. Use
  `get_semesters()` instead.

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
