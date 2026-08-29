# vitap-vtop-client Documentation

Welcome to the `vitap-vtop-client` documentation. This library provides a Pythonic interface to interact with the VIT-AP VTOP student portal, simplifying tasks like fetching academic data, profile information, and more.

## Table of Contents
1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Getting Started](#3-getting-started)
    - [Initializing the Client](#initializing-the-client)
    - [Basic Usage Pattern](#basic-usage-pattern)
4. [API Reference](#4-api-reference)
    - [`VtopClient`](#vtopclient)
        - [`get_attendance(sem_sub_id)`](#get_attendance)
        - [`get_biometric(date)`](#get_biometric)
        - [`get_timetable(sem_sub_id)`](#get_timetable)
        - [`get_grade_history()`](#get_grade_history)
        - [`get_mentor()`](#get_mentor)
        - [`get_profile()`](#get_profile)
5. [Data Models](#5-data-models)
    - [`AttendanceModel`](#attendancemodel)
    - [`BiometricModel`](#biometricmodel)
    - [`TimetableModel`](#timetablemodel)
    - [`GradeHistoryModel`](#gradehistorymodel)
    - [`MentorModel`](#mentormodel)
    - [`StudentProfileModel`](#studentprofilemodel)
    - [`LoggedInStudent`](#loggedinstudent)
6. [Error Handling](#6-error-handling)
7. [Semester IDs (`sem_sub_id`)](#7-semester-ids-sem_sub_id)
8. [Contributing](#8-contributing)
9. [Code of Conduct](#9-code-of-conduct)
10. [License](#10-license)

## 1. Introduction

`vitap-vtop-client` is an asynchronous Python library designed to abstract the complexities of web scraping, session management, and CAPTCHA handling for the VIT-AP VTOP portal. It provides structured data access to various student information sections, making it easier to build applications that leverage VTOP data.

**Disclaimer:** Use this library responsibly and in accordance with VIT-AP's terms of service. Web scraping is subject to changes in the target website's structure, which may occasionally affect the library's functionality.

## 2. Installation

To use the library, clone the repository and install the required dependencies:

```bash
git clone https://github.com/Udhay-Adithya/vitap-vtop-client.git
cd vitap-vtop-client
pip install -r requirements.txt
```

For more detailed setup information, please see [CONTRIBUTING.md](CONTRIBUTING.md).

## 3. Getting Started

### Initializing the Client

The primary interface to the library is the `VtopClient` class. You need to initialize it with your VTOP registration number and password.

```python
from vitap_vtop_client.client import VtopClient

async def main():
    client = VtopClient("your_registration_number", "your_password")
    # ... use the client ...
    await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Basic Usage Pattern

The client is designed to be used with an `async with` statement, which handles session management and closing the client automatically.

```python
import asyncio
from vitap_vtop_client.client import VtopClient
from vitap_vtop_client.exceptions import VitapVtopClientError, VtopLoginError

async def main():
    async with VtopClient("your_registration_number", "your_password") as client:
        try:
            # Example: Fetch profile
            profile = await client.get_profile()
            print(profile)
        except VtopLoginError as e:
            print(f"Login failed: {e}")
        except VitapVtopClientError as e:
            print(f"A client error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. API Reference

### `VtopClient`

The main class for interacting with VTOP.

```python
from vitap_vtop_client.client import VtopClient
Constructor
VtopClient(
    username: str,
    password: str,
    max_login_retries: int = 3,
    captcha_retries: int = 5,
    user_agent: str | None = None,
)
```

**`user_agent`** — the browser identity every request on this session carries.
VTOP binds a session to the User-Agent that created it, so it is fixed for the
life of the client, and anything reusing the session out of process must send
the identical value. Pass the real device's User-Agent when you know it;
otherwise `DEFAULT_USER_AGENT` is used.

#### Session properties and helpers

-   `client.is_authenticated` (bool) — whether a live session is held.
-   `client.user_agent` (str) — the identity described above.
-   `client.get_cookie()` (str) — this session's cookies as a `Cookie` header
    value, e.g. `"JSESSIONID=..."`, so something outside the client (an in-app
    VTOP WebView) can reuse the session without logging in again. It must send
    the same `user_agent`. Raises `VtopSessionError` if not logged in yet.

#### `get_attendance(sem_sub_id: str)`
Fetches attendance data for the specified semester.

-   **Parameters:**
    -   `sem_sub_id` (str): The semester ID (e.g., `"AP2024252"`). See [Semester IDs](#7-semester-ids-sem_sub_id) for common values.
-   **Returns:** `list[AttendanceModel]` - A list of attendance records.
-   **Raises:** `VtopAttendanceError`, `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    fall_sem_2024_25 = "AP2024252" # Example Semester ID
    attendance_data = await client.get_attendance(sem_sub_id=fall_sem_2024_25)
    for course_attendance in attendance_data:
        print(f"Course: {course_attendance.course_name}, Percentage: {course_attendance.attendance_percentage}%")
    ```

#### `get_biometric(date: str)`
Fetches biometric (entry/exit) logs for a specific date.

-   **Parameters:**
    -   `date` (str): The date in `"dd/mm/yyyy"` format (e.g., `"01/08/2024"`).
-   **Returns:** `list[BiometricModel]` - A list of biometric log entries.
-   **Raises:** `VtopBiometricError`, `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    biometric_logs = await client.get_biometric(date="01/08/2024")
    for log in biometric_logs:
        print(f"Time: {log.time}, Location: {log.location}")
    ```

#### `get_timetable(sem_sub_id: str)`
Fetches the timetable for the specified semester.

-   **Parameters:**
    -   `sem_sub_id` (str): The semester ID. See [Semester IDs](#semester-ids-sem_sub_id).
-   **Returns:** `TimetableModel` - An object representing the timetable.
-   **Raises:** `VtopTimetableError`, `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    fall_sem_2024_25 = "AP2024252" # Example Semester ID
    timetable = await client.get_timetable(sem_sub_id=fall_sem_2024_25)
    if timetable and timetable.days: # TimetableModel might be empty if no data
        for day, slots in timetable.days.items():
            print(f"\n--- {day} ---")
            for slot_info in slots:
                 for time_slot, course_details in slot_info.items():
                    print(f"  {time_slot}: {course_details}")
    else:
        print("Timetable data not found or empty.")
    ```

#### `get_grade_history()`
Fetches the student's grade history (CGPA, credits registered/earned).

-   **Returns:** `GradeHistoryModel` - An object containing grade history details.
-   **Raises:** `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`, `VtopGradeHistoryError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    grade_info = await client.get_grade_history()
    print(f"CGPA: {grade_info.cgpa}")
    print(f"Credits Earned: {grade_info.credits_earned}")
    ```

#### `get_mentor()`
Fetches details of the student's assigned mentor.

-   **Returns:** `MentorModel` - An object containing mentor details.
-   **Raises:** `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`, `VtopMentorError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    mentor_details = await client.get_mentor()
    print(f"Mentor Name: {mentor_details.faculty_name}")
    print(f"Mentor Email: {mentor_details.faculty_email}")
    ```

#### `get_profile()`
Fetches the complete student profile, including personal details, mentor information, and grade history.

-   **Returns:** `StudentProfileModel` - An object containing comprehensive student profile data.
-   **Raises:** `VtopLoginError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`, `VtopProfileError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    profile = await client.get_profile()
    print(f"Registration number: {profile.registration_number}")
    print(f"Name: {profile.student_name}")
    print(f"Email: {profile.email}")
    if profile.mentor_details:
        print(f"Mentor: {profile.mentor_details.faculty_name}")
    if profile.grade_history:
        print(f"CGPA: {profile.grade_history.cgpa}")
    # Access profile.base64_pfp for the profile picture
    ```

#### `get_exam_schedule(sem_sub_id: str)`
Fetches all the available exam schedules for the specified semester.

-   **Parameters:**
    -   `sem_sub_id` (str): The semester ID. See [Semester IDs](#semester-ids-sem_sub_id).
-   **Returns:** `ExamScheduleModel` - An object representing the exam schedules.
-   **Raises:** `VtopExamScheduleError`, `VtopLoginError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    fall_sem_2024_25 = "AP2024252" # Example Semester ID
    exam_schedule = await client.get_exam_schedule(sem_sub_id=fall_sem_2024_25)
    if exam_schedule: # ExamScheduleModel might be empty if no exams found
        print(exam_schedule)
    else:
        print("Exams not found or empty.")
    ```

#### `get_marks(sem_sub_id: str)`
Fetches available marks for the specified semester.

-   **Parameters:**
    -   `sem_sub_id` (str): The semester ID. See [Semester IDs](#semester-ids-sem_sub_id).
-   **Returns:** `MarksModel` - An object representing the exam schedules.
-   **Raises:** `VtopMarksError`, `VtopLoginError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    fall_sem_2024_25 = "AP2024252" # Example Semester ID
    marks = await client.get_marks(sem_sub_id=fall_sem_2024_25)
    if marks: # MarksModel might be empty if no exams found
        print(marks)
    else:
        print("marks not found or empty.")
    ```

#### `get_weekend_outing_requests()`
Fetches the previously made weekend outing requests.

-   **Returns:** `WeekendOutingModel` - A list of  previously made weekend outing requests.
-   **Raises:** `VtopWeekendOutingError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    reqs = await client.get_weekend_outing_requests()
    if reqs:
        print(reqs)
    ```

#### `get_general_outing_requests()`
Fetches the previously made general outing requests.

-   **Returns:** `GeneralOutingModel` - A list of  previously made general outing requests.
-   **Raises:** `VtopGeneralOutingError`, `VtopSessionError`, `VtopConnectionError`, `VtopParsingError`.
-   **Example:**
    ```python
    # ... inside async with VtopClient ...
    reqs = await client.get_general_outing_requests()
    if reqs:
        print(reqs)
    ```

## 5. Data Models

The library uses Pydantic models to structure the data returned from VTOP.

Refer to the model definitions in:

-   [`vitap_vtop_client/outing/model/general_outing_model.py`](vitap_vtop_client/outing/model/general_outing_model.py) for `GeneralOutingModel`

-   [`vitap_vtop_client/attendance/model/attendance_model.py`](vitap_vtop_client/outing/model/weekend_outing_model.py) for `WeekendOutingModel`

-   [`vitap_vtop_client/marks/model/marks_model.py`](vitap_vtop_client/marks/model/marks_model.py) for `MarksModel`

-   [`vitap_vtop_client/exam_schedule/model/exam_schedule_model.py`](vitap_vtop_client/exam_schedule/model/exam_schedule_model.py) for `ExamScheduleModel`

-   [`vitap_vtop_client/attendance/model/attendance_model.py`](vitap_vtop_client/attendance/model/attendance_model.py) for `AttendanceModel`

-   [`vitap_vtop_client/biometric/model/biometric_model.py`](vitap_vtop_client/biometric/model/biometric_model.py) for `BiometricModel`

-   [`vitap_vtop_client/timetable/model/timetable_model.py`](vitap_vtop_client/timetable/model/timetable_model.py) for `TimetableModel`

-   [`vitap_vtop_client/grade_history/model/grade_history_model.py`](vitap_vtop_client/grade_history/model/grade_history_model.py) for `GradeHistoryModel`

-   [`vitap_vtop_client/mentor/model/mentor_model.py`](vitap_vtop_client/mentor/model/mentor_model.py) for `MentorModel`

-   [`vitap_vtop_client/profile/model/profile_model.py`](vitap_vtop_client/profile/model/profile_model.py) for `StudentProfileModel`

-   [`vitap_vtop_client/login/model/login_model.py`](vitap_vtop_client/login/model/login_model.py) for `LoggedInStudent`


## 6. Error Handling

The library defines custom exceptions to handle various error scenarios. All custom exceptions inherit from `VitapVtopClientError`.

-   `VtopLoginError`: Issues during the login process (e.g., invalid credentials, CAPTCHA failure).
-   `VtopCaptchaError`: Specifically for CAPTCHA solving failures.
-   `VtopConnectionError`: Network-related issues when communicating with VTOP.
-   `VtopSessionError`: Problems with maintaining a valid VTOP session.
-   `VtopCsrfError`: Issues related to CSRF token fetching or validation.
-   `VtopParsingError`: Errors encountered while parsing HTML responses from VTOP.
-   `VtopAttendanceError`: Specific errors during attendance fetching.
-   `VtopBiometricError`: Specific errors during biometric data fetching.
-   `VtopTimetableError`: Specific errors during timetable fetching.
-   `VtopGradeHistoryError`: Specific errors during grade history fetching.
-   `VtopMentorError`: Specific errors during mentor details fetching.
-   `VtopProfileError`: Specific errors during student profile fetching.

Always wrap API calls in `try...except` blocks to handle these potential errors gracefully.

```python
from vitap_vtop_client.exceptions import VitapVtopClientError, VtopLoginError, VtopParsingError

try:
    # API call
    data = await client.get_attendance(sem_sub_id="AP2024252")
except VtopLoginError as e:
    print(f"Login Error: {e}")
except VtopParsingError as e:
    print(f"Parsing Error: {e}")
except VitapVtopClientError as e: # Catch-all for library-specific errors
    print(f"Client Error: {e}")
except Exception as e: # General Python errors
    print(f"An unexpected error: {e}")
```

## 7. Semester IDs (`sem_sub_id`)

Many functions require a `sem_sub_id` to specify the semester. These IDs are specific to VIT-AP's VTOP system.

Fetch them with `get_semesters()`, which reads the semesters VTOP currently
offers for your account.

It tries the timetable page first (that list is scoped to your own semesters),
then falls back to the marks and exam schedule pages, which render the full
institutional list. Without the fallback the list comes back empty for students
who have no timetable yet — freshers especially — which looked like
"No semesters available":

```python
async with VtopClient("username", "password") as client:
    data = await client.get_semesters()
    for semester in data.semesters:
        print(semester.id, semester.name)

    # Use an id from the list for semester scoped calls
    attendance = await client.get_attendance(sem_sub_id=data.semesters[0].id)
```

> A hardcoded `SemSubID` dictionary used to live in `constants.py`. It was
> removed in `0.3.0` because it went stale as new semesters were added and
> silently produced wrong ids. Use `get_semesters()` instead.

## 8. Contributing

Contributions are highly welcome! Whether it's bug fixes, feature enhancements, or documentation improvements, please feel free to contribute.
Please read the [CONTRIBUTING.md](/CONTRIBUTING.md) file for guidelines on how to contribute to this project, including development setup and pull request procedures.

## 9. Code of Conduct

All participants are expected to follow the [CODE_OF_CONDUCT.md](/CODE_OF_CONDUCT.md). Please ensure you are familiar with its contents.

## 10. License

This project is licensed under the Apache License, Version 2.0. See the [`LICENSE`](/LICENSE) for details.