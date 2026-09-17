from typing import List
import httpx
import asyncio

from .constants import VTOP_BASE_URL, DEFAULT_USER_AGENT
from .ssl_config import create_vtop_ssl_context

from .exceptions import (
    VtopLoginError,
    VtopLoginOtpRequiredError,
    VtopCaptchaError,
    VtopCaptchaSolvingError,
    VtopConnectionError,
    VtopSessionError,
    VitapVtopClientError,
    VtopMenuUnavailableError,
)

from .login import (
    fetch_csrf_token,
    pre_login,
    fetch_captcha,
    student_login,
    verify_login_otp,
    resend_login_otp,
    LoggedInStudent,
    RestorableSession,
)

from .utils import solve_captcha, is_menu_unavailable, validate_semester_id

from .attendance import (
    fetch_attendance,
    fetch_attendance_detail,
    fetch_capstone_attendance,
    AttendanceModel,
    AttendanceDetailModel,
    CapstoneAttendanceModel,
)
from .biometric import fetch_biometric, BiometricModel
from .timetable import fetch_timetable, TimetableModel
from .grade_history import fetch_grade_history, GradeHistoryModel
from .mentor import fetch_mentor_info, MentorModel
from .profile import fetch_profile, StudentProfileModel
from .exam_schedule import fetch_exam_schedule, ExamScheduleModel
from .marks import fetch_marks, MarksModel
from .outing import (
    fetch_general_outing_requests,
    fetch_weekend_outing_requests,
    submit_general_outing_request,
    submit_weekend_outing_request,
    delete_general_outing_request,
    delete_weekend_outing_request,
    fetch_general_outing_pdf,
    fetch_weekend_outing_pdf,
    WeekendOutingModel,
    GeneralOutingModel,
)
from .payments import (
    fetch_pending_payments,
    fetch_payment_receipts,
    fetch_payment_receipt_document,
    PendingPayment,
    PaymentReceipt,
)
from .semester import fetch_semesters, SemesterData
from .academic_calendar import (
    init_calendar_page,
    fetch_calendar_class_groups,
    fetch_calendar_months,
    fetch_calendar_month,
    fetch_academic_calendar,
    DEFAULT_CLASS_GROUP,
    AcademicCalendarModel,
    CalendarDayModel,
    CalendarMonthRefModel,
    ClassGroupModel,
)
from .grade_view import (
    fetch_grade_view,
    fetch_grade_view_detail,
    GradeViewCourse,
    GradeViewDetail,
)
from .faculty import (
    fetch_faculty_search,
    fetch_all_faculty,
    fetch_faculty_details,
    FacultyModel,
    FacultyDetailsModel,
)
from .course_page import (
    init_course_page,
    fetch_courses_for_course_page,
    fetch_slots_for_course_page,
    fetch_course_detail,
    download_course_material,
    download_course_plan_excel,
    CoursesResponseModel,
    SlotsResponseModel,
    CoursePageDetailModel,
)
from .digital_assignment import (
    fetch_all_digital_assignments,
    fetch_per_course_dassignments,
    fetch_da_or_qp_pdf,
    upload_course_dassignment,
    verify_assignment_upload_otp,
    DigitalAssignmentModel,
    AssignmentRecordModel,
)


# Passed as the password by VtopClient.restore, and never by anything else. A
# restored client holds a live session instead of credentials, so it has to skip
# the password check -- but doing that with a public keyword argument would put
# an internal flag in the class signature and make `password` look optional.
_RESTORED_SESSION = "\x00restored-session"


class VtopClient:
    """
    An asynchronous client for interacting with the VIT-AP VTOP portal.
    """

    def __init__(
        self,
        registration_number: str,
        password: str,
        max_login_retries: int = 3,
        captcha_retries: int = 5,
        user_agent: str | None = None,
    ):
        """
        Initializes the VtopClient.

        Args:
            uregistration_numbersername: The VTOP registration number.
            password: The VTOP password.
            max_login_retries: Maximum number of overall login attempts.
            captcha_retries: Maximum number of captcha fetch/solve attempts per login.
            user_agent: Browser identity every request on this session carries.
                Fixed for the life of the client so the session presents one
                consistent identity. VTOP was not observed to require that a
                reused session match it, so anything reusing the session out of
                process (an in-app VTOP WebView) is advised but not required to
                send the same value. Defaults to `DEFAULT_USER_AGENT`.
        """
        # A restored client holds a live session instead of credentials, so it
        # can never log in again on its own. _ensure_logged_in checks this
        # rather than silently failing a login with an empty credential.
        restored = password is _RESTORED_SESSION

        if not registration_number or (not password and not restored):
            raise VtopLoginError(
                "Registration number and password are required for VtopClient.",
                status_code=400,
            )
        # validate_registration_number(registration_number)

        self.username = registration_number.upper()
        self.password = None if restored else password
        self._restored = restored
        # VTOP omits an intermediate CA from its TLS chain, so a custom SSL
        # context (certifi roots + the bundled intermediate) is needed to
        # verify it. See ssl_config for details.
        self._user_agent = (user_agent or "").strip() or DEFAULT_USER_AGENT

        async def _reject_dead_session(response: httpx.Response) -> None:
            # A stale or wrong _csrf does not redirect to the login page and
            # does not come back as the rejection modal. Spring's CSRF filter
            # refuses the request before it is routed, so Tomcat answers with
            # its own 404 page. Every url we post to is a constant that exists,
            # so a 404 here means the token or session is dead, not that the
            # path is wrong.
            #
            # Runs before the modal check because it only reads the status, so
            # a dead session never pays for the body.
            if response.status_code == 404 and response.request.method == "POST":
                raise VtopSessionError(
                    "VTOP rejected the request with a 404, which is what it "
                    "does when the session or CSRF token has expired. Log in "
                    "again before retrying.",
                    status_code=401,
                )

        async def _reject_menu_unavailable(response: httpx.Response) -> None:
            # VTOP answers a rejected request with a generic modal and an HTTP
            # 200, so raise_for_status() lets it through and the fragment
            # reaches a parser that cannot make sense of it. Catch it here,
            # once, rather than in every fetch function.
            await response.aread()
            if is_menu_unavailable(response.text):
                raise VtopMenuUnavailableError(
                    f"VTOP refused to answer {response.request.url.path}. Its "
                    "response is the same whether the request shape was wrong "
                    "or the menu is switched off.",
                    status_code=502,
                )

        async def _pin_user_agent(request: httpx.Request) -> None:
            # Fetch functions pass their own headers, which httpx merges with
            # request headers winning. Rewriting here runs after that merge, so
            # every request on this session carries the same identity.
            request.headers["User-Agent"] = self._user_agent

        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            base_url=VTOP_BASE_URL,
            verify=create_vtop_ssl_context(),
            event_hooks={
                "request": [_pin_user_agent],
                "response": [_reject_dead_session, _reject_menu_unavailable],
            },
        )
        self._logged_in_student: LoggedInStudent | None = None
        self.max_login_retries = max_login_retries
        self.captcha_retries = captcha_retries
        self._login_lock = asyncio.Lock()  # Prevents concurrent login attempts
        # CSRF token scraped from the OTP page. Set when VTOP interrupts the
        # login with an OTP challenge, cleared once the OTP is verified.
        self._pending_otp_csrf: str | None = None

    @property
    def otp_pending(self) -> bool:
        """True when VTOP is waiting on an OTP to finish the login."""
        return self._pending_otp_csrf is not None

    @property
    def is_authenticated(self) -> bool:
        """True when this client holds a live, logged-in session."""
        return self._logged_in_student is not None

    @property
    def user_agent(self) -> str:
        """The browser identity every request on this session carries."""
        return self._user_agent

    def get_cookie(self) -> str:
        """
        Returns this session's cookies as a `Cookie` header value.

        Lets something outside this client reuse the authenticated session —
        an in-app VTOP WebView, for example — without logging in again. The
        consumer is advised to send the same `User-Agent` (see `user_agent`) so
        the session keeps one consistent identity, though VTOP was not observed
        to require it.

        Returns:
            str: e.g. `"JSESSIONID=...; other=..."`, empty if there are none.

        Raises:
            VtopSessionError: If the client is not logged in yet.
        """
        if not self.is_authenticated:
            raise VtopSessionError(
                "Not logged in. Call login() before exporting session cookies.",
                status_code=409,
            )
        return "; ".join(
            f"{cookie.name}={cookie.value}" for cookie in self._client.cookies.jar
        )

    @property
    def session(self) -> RestorableSession:
        """
        Everything needed to rebuild this client elsewhere.

        Pair this with `VtopClient.restore`. Handing these three values to
        another process lets it act on the same VTOP session without logging
        in again, which matters because VTOP's login is captcha gated and may
        demand an OTP the user has to read from their email.

        Returns:
            RestorableSession: The cookie, the post-login CSRF token, the
                registration number and the User-Agent this session uses.

        Raises:
            VtopSessionError: If the client is not logged in yet.
        """
        student = self._logged_in_student
        if student is None:
            raise VtopSessionError(
                "Not logged in. Call login() before exporting the session.",
                status_code=409,
            )
        return RestorableSession(
            registration_number=student.registration_number,
            cookie=self.get_cookie(),
            csrf_token=student.post_login_csrf_token,
            user_agent=self._user_agent,
        )

    @classmethod
    def restore(
        cls,
        registration_number: str,
        cookie: str,
        csrf_token: str,
        user_agent: str | None = None,
    ) -> "VtopClient":
        """
        Rebuilds a client from a session exported by `session`.

        VTOP keeps its session server side against the `JSESSIONID` cookie, so
        a client holding that cookie and the post-login CSRF token can make
        data requests without logging in — verified against live VTOP from a
        process that had never authenticated.

        This is what lets a caller be stateless. A web service can log in once,
        hand these values back to its own client, and take them again on the
        next request, instead of keeping a live VtopClient in memory and losing
        every session when it restarts.

        The returned client has no password. If the session has expired it
        cannot log back in, and raises `VtopSessionError` instead.

        Args:
            registration_number: The student the session belongs to.
            cookie: The `Cookie` header value from `get_cookie()`.
            csrf_token: The `post_login_csrf_token` from `session`.
            user_agent: The agent the session was created with. Advisory —
                VTOP was not observed to enforce it — but passing it keeps one
                identity across the whole session.

        Returns:
            VtopClient: A client ready to make data requests.

        Raises:
            VtopSessionError: If any of the three values is missing.
        """
        if not registration_number or not cookie or not csrf_token:
            raise VtopSessionError(
                "Restoring a session needs the registration number, the "
                "cookie and the post-login CSRF token.",
                status_code=400,
            )

        client = cls(
            registration_number=registration_number,
            password=_RESTORED_SESSION,
            user_agent=user_agent,
        )
        client._logged_in_student = LoggedInStudent(
            registration_number=registration_number.upper(),
            post_login_csrf_token=csrf_token,
        )
        for pair in cookie.split(";"):
            name, sep, value = pair.strip().partition("=")
            if sep and name:
                client._client.cookies.set(name, value)
        return client

    async def login(self) -> LoggedInStudent:
        """
        Logs in to VTOP explicitly.

        VTOP requires an OTP after a period of inactivity or when logging in
        from a new IP address. When that happens this raises
        `VtopLoginOtpRequiredError`; collect the OTP from the user and pass it
        to `verify_login_otp` to finish authenticating.

        Returns:
            LoggedInStudent: The authenticated session details.

        Raises:
            VtopLoginOtpRequiredError: If VTOP requires an OTP to continue.
            VtopLoginError: If the credentials are rejected.
        """
        async with self._login_lock:
            if self._logged_in_student is not None:
                return self._logged_in_student
            return await self._perform_login_sequence()

    async def verify_login_otp(self, otp: str) -> LoggedInStudent:
        """
        Completes a login that VTOP interrupted with an OTP challenge.

        Args:
            otp (str): The OTP entered by the user.

        Returns:
            LoggedInStudent: The authenticated session details.

        Raises:
            VtopSessionError: If no OTP challenge is currently pending.
            VtopLoginOtpIncorrectError: If the OTP is wrong.
            VtopLoginOtpExpiredError: If the OTP has expired.
        """
        if self._pending_otp_csrf is None:
            raise VtopSessionError(
                "No login OTP is pending. Call login() first.", status_code=409
            )

        async with self._login_lock:
            logged_in_student = await verify_login_otp(
                self._client, self._pending_otp_csrf, otp
            )
            self._logged_in_student = logged_in_student
            self._pending_otp_csrf = None
            return logged_in_student

    async def resend_login_otp(self) -> None:
        """
        Asks VTOP to send a fresh login OTP.

        Raises:
            VtopSessionError: If no OTP challenge is currently pending.
            VtopLoginError: If VTOP declines to resend the OTP.
        """
        if self._pending_otp_csrf is None:
            raise VtopSessionError(
                "No login OTP is pending. Call login() first.", status_code=409
            )

        await resend_login_otp(self._client, self._pending_otp_csrf)

    async def _perform_login_sequence(self) -> LoggedInStudent:
        """
        Handles the complete login sequence.
        This sequence must be performed everytime when a user needs something.
        """
        for attempt in range(self.max_login_retries):
            print(
                f"VtopClient: Login attempt {attempt + 1}/{self.max_login_retries} for user {self.username[:5]}****"
            )
            try:
                # Step 1: Fetch initial CSRF token
                csrf_token = await fetch_csrf_token(self._client)
                print(
                    f"VtopClient: CSRF TOKEN: {csrf_token[:8]} - **** - **** - ************"
                )

                # Step 2: Pre-login setup
                await pre_login(self._client, csrf_token)

                # Step 3: Fetch and solve CAPTCHA
                captcha_base64 = await fetch_captcha(
                    self._client, retries=self.captcha_retries
                )
                captcha_value = await asyncio.to_thread(solve_captcha, captcha_base64)
                print(f"VtopClient: Solved captcha: {captcha_value}")

                # Step 4: Attempt login
                logged_in_student = await student_login(
                    self._client,
                    csrf_token,
                    self.username,
                    self.password,
                    captcha_value,
                )
                self._logged_in_student = logged_in_student
                print(f"VtopClient: Login successful for {self.username[:5]}****")
                return logged_in_student

            except VtopCaptchaError as e:
                print(f"VtopClient: Captcha error during login: {e}")
                if attempt == self.max_login_retries - 1:
                    raise
                await asyncio.sleep(1)  # Wait a bit before retrying captcha

            except VtopCaptchaSolvingError as e:
                print(f"VtopClient: Captcha solving failed during login: {e}")
                if attempt == self.captcha_retries - 1:
                    raise
                await asyncio.sleep(1)  # Wait a bit before retrying captcha

            except VtopLoginOtpRequiredError as e:
                # Credentials and captcha were accepted; VTOP just wants an OTP.
                # Stash the OTP page's CSRF token and hand control back to the
                # caller so it can collect the OTP from the user.
                print("VtopClient: VTOP requires an OTP to complete the login.")
                self._pending_otp_csrf = e.csrf_token
                raise

            except VtopLoginError as e:  # Typically for bad credentials
                print(
                    f"VtopClient: Login failed due to invalid credentials or format: {e}"
                )
                raise  # No point retrying if credentials are bad
            except VtopConnectionError as e:
                raise

            except VtopSessionError as e:
                print(f"Session error (e.g., CSRF/session expired): {e}")
                raise
            except Exception as e:
                print(f"VtopClient: Unexpected error during login: {e}")
                if attempt == self.max_login_retries - 1:
                    raise VitapVtopClientError(
                        f"Login failed after {self.max_login_retries} attempts due to unexpected error: {e}"
                    )
                await asyncio.sleep(attempt + 1)

        # Should not be reached if loop completes without returning/raising
        raise VitapVtopClientError(
            f"Login failed for user {self.username} after {self.max_login_retries} attempts."
        )

    async def _ensure_logged_in(self) -> LoggedInStudent:
        """
        Ensures the client is logged in. If not, performs login.
        This method is idempotent.

        Raises:
            VtopSessionError: If a login OTP is pending. Retrying the login
                here would invalidate the OTP already sent to the user, so the
                caller must resolve it via `verify_login_otp` instead.
        """
        # Check if already logged in and session is potentially valid
        if self._logged_in_student is not None:
            return self._logged_in_student

        if self._pending_otp_csrf is not None:
            raise VtopSessionError(
                "Login is awaiting OTP verification. Call verify_login_otp() "
                "with the OTP sent by VTOP before requesting data.",
                status_code=409,
            )

        if self._restored:
            # Restored from an exported session, so there is no password to log
            # in with. The session it was given is gone; the caller has to run
            # a fresh login, which may need an OTP they have to answer.
            raise VtopSessionError(
                "This client was restored from an exported session and that "
                "session is no longer valid. Log in again with credentials.",
                status_code=401,
            )

        async with self._login_lock:
            # Double-check after acquiring the lock, in case another coroutine logged in
            if self._logged_in_student is None:
                print(
                    f"VtopClient: Not logged in or session expired for {self.username[:5]}****. Initiating login."
                )
                await self._perform_login_sequence()

            if (
                self._logged_in_student is None
            ):  # Should be set by _perform_login_sequence on success
                raise VitapVtopClientError(
                    "VtopClient: Failed to establish a login session."
                )
            return self._logged_in_student

    async def get_semesters(self) -> SemesterData:
        """
        Fetches the semesters available to the student.

        The ids returned here are what every semester scoped method expects.
        Take them from this call rather than storing them, because **VTOP does
        not reject an unknown semester id** -- it answers with a normal, empty
        result. A stale id from a previous term therefore looks exactly like a
        semester in which the student has no data, and nothing downstream can
        tell the difference.

        Semester scoped methods check the *shape* of an id (`AP` and seven
        digits) and reject a typo, but a well formed id that is simply wrong
        cannot be caught here. Choosing a real one from this list is the
        caller's responsibility.

        Returns:
            SemesterData: The available semesters and the time they were read.
        """
        student = await self._ensure_logged_in()
        return await fetch_semesters(
            client=self._client,
            username=student.registration_number,
            csrf_token=student.post_login_csrf_token,
        )

    async def get_attendance(self, sem_sub_id: str) -> list[AttendanceModel]:
        """
        Fetches attendance data for the given semester subject ID.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").

        Returns:
            A list containing the parsed attendance data(AttendanceModel).
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_attendance(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            semSubID=sem_sub_id,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_attendance_detail(
        self,
        sem_sub_id: str,
        course_id: str,
        course_type: str,
    ) -> list[AttendanceDetailModel]:
        """
        Fetches the per class attendance detail for a single course.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").
            course_id: The course id, from AttendanceModel.course_id.
            course_type: The short course type code, from
                AttendanceModel.course_type_code.

        Returns:
            A list containing one AttendanceDetailModel per class held.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_attendance_detail(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            semSubID=sem_sub_id,
            course_id=course_id,
            course_type=course_type,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_capstone_attendance(
        self, sem_sub_id: str
    ) -> CapstoneAttendanceModel | None:
        """
        Fetches capstone/SDP attendance for the given semester.

        This is deliberately separate from `get_attendance`: capstone attendance
        is per semester rather than per course, and counts present / on duty /
        absent instead of attended / total, so it does not fit AttendanceModel.
        VTOP returns the tally and the day-by-day calendar together, so both
        arrive in one call.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2026272").

        Returns:
            The CapstoneAttendanceModel, or None when the student has no
            capstone registered for that semester.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_capstone_attendance(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            semSubID=sem_sub_id,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_calendar_class_groups(
        self, sem_sub_id: str
    ) -> List[ClassGroupModel]:
        """
        Fetches the calendar class groups available for a semester.

        Class groups are semester dependent, so they cannot be hardcoded.
        Usually "COMB" (All Class Group Combined) and one or more specific
        groups.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2026272").
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_calendar_class_groups(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_calendar_months(
        self, sem_sub_id: str, class_group_id: str = DEFAULT_CLASS_GROUP
    ) -> List[CalendarMonthRefModel]:
        """
        Fetches the months a semester's calendar covers.

        Each entry carries the `cal_date` that `get_calendar_month` expects.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2026272").
            class_group_id: From `get_calendar_class_groups`. Defaults to the
                combined group.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_calendar_months(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            classGroupID=class_group_id,
        )

    async def get_calendar_month(
        self,
        sem_sub_id: str,
        cal_date: str,
        class_group_id: str = DEFAULT_CLASS_GROUP,
    ) -> List[CalendarDayModel]:
        """
        Fetches one month of the academic calendar.

        VTOP renders the month as a week grid; this returns it as a flat,
        date-ordered list of days, since the grid is a display concern.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2026272").
            cal_date: From `CalendarMonthRefModel.cal_date`, e.g. "01-AUG-2026".
            class_group_id: From `get_calendar_class_groups`.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_calendar_month(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            cal_date=cal_date,
            classGroupID=class_group_id,
        )

    async def get_academic_calendar(
        self, sem_sub_id: str, class_group_id: str = DEFAULT_CLASS_GROUP
    ) -> AcademicCalendarModel:
        """
        Fetches a semester's whole academic calendar.

        Convenience over the three calls above: it opens the page, reads the
        month list, fetches every month, and flattens them into one
        date-ordered list of days. That is one request per month — six for a
        typical semester — so prefer `get_calendar_month` for a single month.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2026272").
            class_group_id: From `get_calendar_class_groups`.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_academic_calendar(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            classGroupID=class_group_id,
        )

    async def get_biometric(self, date: str) -> list[BiometricModel]:
        """
        Fetches biometric data for the given date.

        Args:
            date: The date for which the biometric log is requested, in 'dd/mm/yyyy' format.

        Returns:
            A list containing the parsed biometric data(AttendanceModel).
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_biometric(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            date=date,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_timetable(self, sem_sub_id: str) -> TimetableModel:
        """
        Fetches timetable data for the given semester.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").

        Returns:
            A TimetableModel containing the parsed timetable details.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_timetable(
            client=self._client,
            username=logged_in_info.registration_number,
            semSubID=sem_sub_id,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_grade_view(self, sem_sub_id: str) -> List[GradeViewCourse]:
        """
        Fetches the graded courses for a semester.

        Grades appear only once a semester has ended; the current semester
        returns nothing until results are published. Each course carries a
        course_id for `get_grade_view_detail`.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2025264").

        Returns:
            A list of GradeViewCourse, one per graded course.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_grade_view(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_grade_view_detail(
        self, sem_sub_id: str, course_id: str
    ) -> GradeViewDetail:
        """
        Fetches the mark breakdown and class statistics for one course.

        This is the data behind an expandable tile on the grade view page: the
        per-component marks (CAT, FAT, quizzes) plus the class mean, standard
        deviation and grade cutoffs.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2025264").
            course_id: The course id, from GradeViewCourse.course_id.

        Returns:
            The GradeViewDetail for the course.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_grade_view_detail(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            course_id=course_id,
        )

    async def get_grade_history(self) -> GradeHistoryModel:
        """
        Fetches grade history for the given registration_number.

        Returns:
            A GradeHistoryModel containing the parsed grade history details.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_grade_history(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_mentor(self) -> MentorModel:
        """
        Fetches mentor data for the given registration_number.

        Returns:
            A MentorModel containing the parsed mentor data.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_mentor_info(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_profile(
        self,
        include_grade_history: bool = True,
        include_mentor: bool = True,
    ) -> StudentProfileModel:
        """
        Fetches profile data for the given registration_number.

        The profile page does not carry the grade history or the mentor, so
        each of those is a further request. They are fetched concurrently.

        Grade history is the largest response the client fetches anywhere,
        around 137KB. If you only need the profile itself, turn it off.

        Args:
            include_grade_history: Fetch the nested grade history. Defaults to
                True, which costs an extra request of roughly 137KB.
            include_mentor: Fetch the nested mentor details. Defaults to True,
                which costs an extra request.

        Returns:
            A StudentProfileModel containing the parsed student details.
            Anything not requested is left at its model default.
        """
        logged_in_info = await self._ensure_logged_in()
        profile = await fetch_profile(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            include_grade_history=include_grade_history,
            include_mentor=include_mentor,
        )
        # The profile page never renders the registration number, so attach the
        # one captured from `authorizedIDX` at login.
        profile.registration_number = logged_in_info.registration_number
        return profile

    async def get_exam_schedule(self, sem_sub_id: str) -> ExamScheduleModel:
        """
        Fetches all exam schedules for the given semester.

        Returns:
            A ExamScheduleModel containing the parsed exam schedule details.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_exam_schedule(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_marks(self, sem_sub_id: str) -> MarksModel:
        """
        Fetches all marks for the given semester.

        Returns:
            A MarksModel containing the parsed mark details.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_marks(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_weekend_outing_requests(self) -> WeekendOutingModel:
        """
        Fetches all the previously submitted Weekend Outing requests.

        Returns:
            A WeekendOutingModel containing the previously submitted Weekend Outing details.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_weekend_outing_requests(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_general_outing_requests(self) -> GeneralOutingModel:
        """
        Fetches all the previously submitted Genneral Outing requests.

        Returns:
            A GeneralOutingModel containing the previously submitted General Outing details.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_general_outing_requests(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_pending_payments(self) -> List[PendingPayment]:
        """
        Fetches a list of pending payments.

        Returns:
            A list of PendingPayment if found or an empty list.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_pending_payments(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_payment_receipts(self) -> List[PaymentReceipt]:
        """
        Fetches a list of previously made payment receipts.

        Returns:
            A list of PaymentReceipt if found or an empty list.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_payment_receipts(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def init_course_page(self) -> str:
        """
        Opens the course page.

        VTOP requires this before it will answer `get_course_page_courses`
        and `get_course_page_slots`.

        Returns:
            The course page markup.
        """
        logged_in_info = await self._ensure_logged_in()
        return await init_course_page(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_course_page_courses(
        self, sem_sub_id: str
    ) -> CoursesResponseModel:
        """
        Fetches the courses selectable on the course page for a semester.

        Call `init_course_page` first.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").

        Returns:
            The selectable courses.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_courses_for_course_page(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_course_page_slots(
        self, sem_sub_id: str, class_id: str
    ) -> SlotsResponseModel:
        """
        Fetches the slots and class rows for a course.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").
            class_id: The course value, from CourseOptionModel.value.

        Returns:
            The selectable slots and the class rows.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_slots_for_course_page(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            class_id=class_id,
        )

    async def get_course_detail(
        self, sem_sub_id: str, erp_id: str, class_id: str
    ) -> CoursePageDetailModel:
        """
        Fetches a course's detail page, with lectures and material links.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").
            erp_id: The faculty ERP id, from CourseClassEntryModel.erp_id.
            class_id: The class id, from CourseClassEntryModel.class_id.

        Returns:
            The course summary, lectures and download paths.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_course_detail(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            erp_id=erp_id,
            class_id=class_id,
        )

    async def download_course_material(self, download_path: str) -> bytes:
        """
        Downloads a course material, syllabus or bundled material archive.

        Args:
            download_path: A path from CoursePageDetailModel, such as
                download_all_path, syllabus_download_path, or a lecture's
                reference material download_path.

        Returns:
            The raw file contents.
        """
        logged_in_info = await self._ensure_logged_in()
        return await download_course_material(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            download_path=download_path,
        )

    async def download_course_plan(self, sem_sub_id: str, class_id: str) -> bytes:
        """
        Downloads a course plan as an Excel workbook.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").
            class_id: The class id, from CourseClassEntryModel.class_id.

        Returns:
            The raw workbook contents.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await download_course_plan_excel(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
            class_id=class_id,
        )

    async def submit_general_outing(
        self,
        out_place: str,
        purpose_of_visit: str,
        outing_date: str,
        out_time: str,
        in_date: str,
        in_time: str,
    ) -> str:
        """
        Submits a general outing request.

        Args:
            out_place: The place being visited.
            purpose_of_visit: The reason for the outing.
            outing_date: The date of leaving, as VTOP expects it.
            out_time: The time of leaving.
            in_date: The date of returning.
            in_time: The time of returning.

        Returns:
            VTOP's response message.
        """
        logged_in_info = await self._ensure_logged_in()
        return await submit_general_outing_request(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            outPlace=out_place,
            purposeOfVisit=purpose_of_visit,
            outingDate=outing_date,
            outTime=out_time,
            inDate=in_date,
            inTime=in_time,
        )

    async def submit_weekend_outing(
        self,
        out_place: str,
        purpose_of_visit: str,
        outing_date: str,
        out_time: str,
        contact_number: str,
    ) -> str:
        """
        Submits a weekend outing request.

        Args:
            out_place: The place being visited.
            purpose_of_visit: The reason for the outing.
            outing_date: The date of the outing, as VTOP expects it.
            out_time: The time of leaving.
            contact_number: The student's contact number.

        Returns:
            VTOP's response message.
        """
        logged_in_info = await self._ensure_logged_in()
        return await submit_weekend_outing_request(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            outPlace=out_place,
            purposeOfVisit=purpose_of_visit,
            outingDate=outing_date,
            outTime=out_time,
            contactNumber=contact_number,
        )

    async def delete_general_outing(self, leave_id: str) -> str:
        """
        Deletes a general outing request.

        Args:
            leave_id: The leave id, from GeneralOutingRequest.leave_id.

        Returns:
            VTOP's response message.
        """
        logged_in_info = await self._ensure_logged_in()
        return await delete_general_outing_request(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            leave_id=leave_id,
        )

    async def delete_weekend_outing(self, booking_id: str) -> str:
        """
        Deletes a weekend outing request.

        Args:
            booking_id: The booking id, from WeekendOutingRequest.booking_id.

        Returns:
            VTOP's response message.
        """
        logged_in_info = await self._ensure_logged_in()
        return await delete_weekend_outing_request(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            booking_id=booking_id,
        )

    async def download_general_outing_pass(self, leave_id: str) -> bytes:
        """
        Downloads the leave pass PDF for a general outing request.

        Args:
            leave_id: The leave id, from GeneralOutingRequest.leave_id. Check
                can_download first.

        Returns:
            The raw PDF contents.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_general_outing_pdf(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            leave_id=leave_id,
        )

    async def download_weekend_outing_form(self, booking_id: str) -> bytes:
        """
        Downloads the outing form PDF for a weekend outing request.

        Args:
            booking_id: The booking id, from WeekendOutingRequest.booking_id.
                Check can_download first.

        Returns:
            The raw PDF contents.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_weekend_outing_pdf(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            booking_id=booking_id,
        )

    async def download_payment_receipt(
        self, receipt_no: str, application_number: str
    ) -> str:
        """
        Downloads the printable document for a paid receipt.

        VTOP serves this as an HTML page rather than a PDF.

        Args:
            receipt_no: The receipt number, from PaymentReceipt.receipt_no.
            application_number: The student's application number, available
                from StudentProfileModel.application_number.

        Returns:
            The receipt document markup.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_payment_receipt_document(
            client=self._client,
            registration_number=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            receipt_no=receipt_no,
            application_number=application_number,
        )

    async def get_digital_assignments(
        self, sem_sub_id: str
    ) -> List[DigitalAssignmentModel]:
        """
        Fetches every course's assignments for the given semester.

        This issues one additional request per course, since VTOP serves the
        course list and the per course assignments separately.

        Args:
            sem_sub_id: The semester subject ID (e.g., "AP2023242").

        Returns:
            A list of DigitalAssignmentModel with details populated.
        """
        validate_semester_id(sem_sub_id)
        logged_in_info = await self._ensure_logged_in()
        return await fetch_all_digital_assignments(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            semSubID=sem_sub_id,
        )

    async def get_course_assignments(
        self, class_id: str
    ) -> List[AssignmentRecordModel]:
        """
        Fetches the assignments for a single course.

        Args:
            class_id: The class id, from DigitalAssignmentModel.class_id.

        Returns:
            A list of AssignmentRecordModel, one per assignment.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_per_course_dassignments(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            class_id=class_id,
        )

    async def download_assignment_file(self, download_url: str) -> bytes:
        """
        Downloads an assignment question paper or a submitted assignment file.

        Args:
            download_url: The path from AssignmentRecordModel.qp_download_url
                or AssignmentRecordModel.da_download_url.

        Returns:
            The raw file contents.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_da_or_qp_pdf(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            download_url=download_url,
        )

    async def upload_assignment(
        self,
        class_id: str,
        mcode: str,
        file_name: str,
        file_bytes: bytes,
    ) -> str:
        """
        Uploads a file as the submission for one assignment.

        VTOP may hold the upload pending an OTP mailed to the student, in
        which case this raises VtopDigitalAssignmentUploadOtpRequiredError;
        follow up with `verify_assignment_upload_otp`.

        Args:
            class_id: The class id, from DigitalAssignmentModel.class_id.
            mcode: The assignment code, from AssignmentRecordModel.mcode.
            file_name: The file name, used to derive the content type.
            file_bytes: The file contents. Max 4 MB, and one of pdf, doc,
                docx, xls or xlsx.

        Returns:
            VTOP's response message, "Uploaded successfully" on success.
        """
        logged_in_info = await self._ensure_logged_in()
        return await upload_course_dassignment(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            class_id=class_id,
            mcode=mcode,
            file_name=file_name,
            file_bytes=file_bytes,
        )

    async def verify_assignment_upload_otp(self, otp: str) -> str:
        """
        Confirms a held assignment upload with the OTP VTOP mailed.

        Args:
            otp: The OTP entered by the user.

        Returns:
            VTOP's response message, "Uploaded successfully" on success.
        """
        logged_in_info = await self._ensure_logged_in()
        return await verify_assignment_upload_otp(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            otp=otp,
        )

    async def search_faculty(self, search_term: str) -> FacultyModel:
        """
        Searches for a faculty member and returns the first match.

        Args:
            search_term: A faculty name or employee id to search for.

        Returns:
            The first matching FacultyModel, or an empty model when there are
            no matches.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_faculty_search(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            search_term=search_term,
        )

    async def get_all_faculty(self) -> List[FacultyModel]:
        """
        Fetches the full faculty directory.

        Returns:
            A list of FacultyModel, one per faculty member.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_all_faculty(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
        )

    async def get_faculty_details(self, emp_id: str) -> FacultyDetailsModel:
        """
        Fetches a faculty member's profile and office hours.

        Args:
            emp_id: The employee id, from FacultyModel.emp_id.

        Returns:
            The parsed FacultyDetailsModel.
        """
        logged_in_info = await self._ensure_logged_in()
        return await fetch_faculty_details(
            client=self._client,
            username=logged_in_info.registration_number,
            csrf_token=logged_in_info.post_login_csrf_token,
            emp_id=emp_id,
        )

    async def close(self):
        """
        Closes the underlying HTTP client. Should be called when done with the VtopClient.
        """
        await self._client.aclose()

    async def __aenter__(self):
        """Allows using the client with 'async with'."""
        # You could optionally call await self._ensure_logged_in() here
        # if you want to ensure login upon entering the context.
        # However, lazy login (on first actual data request) is often preferred.
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the client when exiting 'async with' block."""
        await self.close()
