import httpx


class VitapVtopClientError(Exception):
    """Base exception for all VITAP VTOP client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class VtopConnectionError(VitapVtopClientError):
    """Raised for network-related errors during VTOP communication."""

    def __init__(
        self,
        message: str,
        original_exception: httpx.RequestError | None = None,
        status_code: int | None = None,
    ):
        # httpx raises its transport errors with an empty message, so a caller
        # building one with f"...: {e}" ends up with a message that stops at
        # the colon -- the failure you most want described is the one that
        # describes itself least. Name the class, which is the only thing that
        # separates a read timeout from a refused connection.
        if original_exception is not None and not str(original_exception):
            message = f"{message.rstrip()} {type(original_exception).__name__}"
        super().__init__(message, status_code)
        self.original_exception = original_exception


class VtopLoginError(VitapVtopClientError):
    """Raised when login fails due to invalid credentials, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopAttendanceError(VitapVtopClientError):
    """Raised when fetching attendance fails due to attendance parsing, invalid semSubId, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopTimetableError(VitapVtopClientError):
    """Raised when fetching timetable fails due to data parsing, invalid semSubId, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopGradeHistoryError(VitapVtopClientError):
    """Raised when fetching greades history fails due to data parsing, invalid semester id, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopMentorError(VitapVtopClientError):
    """Raised when fetching biometric fails due to data parsing, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopBiometricError(VitapVtopClientError):
    """Raised when fetching biometric fails due to data parsing, invalid date, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopProfileError(VitapVtopClientError):
    """Raised when fetching biometric fails due to data parsing, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopExamScheduleError(VitapVtopClientError):
    """Raised when fetching exam schedule fails due to data parsing, invalid semester id, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopMarksError(VitapVtopClientError):
    """Raised when fetching marks fails due to data parsing, invalid semester id, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopGeneralOutingError(VitapVtopClientError):
    """Raised when fetching/posting marks fails due to data parsing, invalid semester id, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopWeekendOutingError(VitapVtopClientError):
    """Raised when fetching/posting marks fails due to data parsing, invalid semester id, server-side validation, etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopCaptchaError(VtopLoginError):
    """Raised for errors specifically related to CAPTCHA fetching."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopCaptchaSolvingError(VtopLoginError):
    """Raised for errors specifically related to CAPTCHA solving."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopCsrfError(VtopLoginError):
    """Raised for errors specifically related to CSRF scraping and fetching."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopLoginOtpRequiredError(VtopLoginError):
    """Raised when VTOP requires an OTP to complete the login.

    VTOP asks for an OTP after a period of inactivity or when the login
    originates from a new IP address. Credentials and captcha have already
    been accepted at this point; the caller must collect the OTP from the
    user and pass it to `VtopClient.verify_login_otp`.

    Carries the CSRF token scraped from the OTP page, which is the token that
    must be submitted alongside the OTP.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        csrf_token: str | None = None,
    ):
        super().__init__(message, status_code)
        self.csrf_token = csrf_token


class VtopLoginOtpIncorrectError(VtopLoginError):
    """Raised when the submitted login OTP is rejected by VTOP."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopLoginOtpExpiredError(VtopLoginError):
    """Raised when the submitted login OTP has expired and must be resent."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentError(VitapVtopClientError):
    """Raised for errors related to digital assignments."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentFileNotFoundError(VtopDigitalAssignmentError):
    """Raised when an assignment upload is attempted without file contents."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentFileTypeNotSupportedError(VtopDigitalAssignmentError):
    """Raised when the assignment file is not a type VTOP accepts."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentFileSizeExceededError(VtopDigitalAssignmentError):
    """Raised when the assignment file is larger than VTOP's 4 MB limit."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentUploadOtpRequiredError(VtopDigitalAssignmentError):
    """Raised when VTOP holds an assignment upload pending OTP confirmation.

    The file has been received but is not submitted until the OTP mailed to
    the student is passed to `VtopClient.verify_assignment_upload_otp`.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopDigitalAssignmentUploadOtpIncorrectError(VtopDigitalAssignmentError):
    """Raised when the assignment upload OTP is rejected by VTOP."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopCalendarError(VitapVtopClientError):
    """Raised for errors related to the academic calendar."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopParsingError(VitapVtopClientError):
    """Raised when data parsing fails unexpectedly (e.g., new HTML format)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)


class VtopSessionError(VitapVtopClientError):
    """Raised when an operation requires an active session but one is not available or valid."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code)
