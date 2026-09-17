# User-Agent used when the caller does not supply one.
#
# The fallback identity for a session.
#
# This is pinned for the life of a client so a session presents one consistent
# identity rather than a different one per request. It is not a protocol
# requirement: as of 2026-09-17 VTOP was not observed to tie a session to the
# User-Agent that created it -- an exported session was reused successfully
# from a different agent entirely. Callers that know the real device should
# still pass its User-Agent to VtopClient; this is the fallback for tools and
# tests.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

# No "Connection: close" here. Sending it closed the socket after every
# response, so each request paid a fresh TCP + TLS handshake, and concurrent
# calls on one session ended up as slow as serial ones. Keeping the connection
# alive is worth ~20ms per request and roughly 2.6x on concurrent fan-out.
HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
}


def build_headers(user_agent: str | None = None) -> dict[str, str]:
    """Returns the shared request headers, optionally with a caller's User-Agent."""
    headers = dict(HEADERS)
    if user_agent and user_agent.strip():
        headers["User-Agent"] = user_agent
    return headers

# Main URL
VTOP_BASE_URL = "https://vtop.vitap.ac.in"
VTOP_URL = "/vtop/open/page"

# Routes
VTOP_LOGIN_INIT_ROUTE = "/vtop/init/page"
VTOP_LOGIN_ERROR_ROUTE = "/vtop/login/error"

# Login Page URL
VTOP_PRELOGIN_URL = "/vtop/prelogin/setup"
VTOP_PRELOGIN_INIT_URL = "/vtop/init/page"
VTOP_LOGIN_URL = "/vtop/login"
VTOP_LOGIN_INIT_URL = "/vtop/init/page"
VTOP_LOGIN_ERROR_URL = "/vtop/login/error"

# Login OTP URL
VTOP_VALIDATE_OTP_URL = "/vtop/validateSecurityOtp"
VTOP_RESEND_OTP_URL = "/vtop/resendSecurityOtp"

# Home Page URL
VTOP_HOME_URL = "/vtop/home"

# Content Page URL
VTOP_CONTENT_URL = "/vtop/content"

# Profile URL
PROFILE_URL = "/vtop/studentsRecord/StudentProfileAllView"
STUDENT_IMAGE_UPLOAD_URL = "/vtop/others/photo/getStudentIdPhotoAndSign1"


# Biometric Log URL
BIOMETRIC_LOG_URL = "/vtop/academics/biometriclogdisplay"
GET_BIOMETRIC_LOG_URL = "/vtop/getStudBioHistory"

# Proctor Details URL
MENTOR_DETAILS_URL = "/vtop/proctor/viewProctorDetails"

# HOD Details URL
HOD_DETAILS_URL = "/vtop/hrms/viewHodDeanDetails"

# Payment URL
PAYMENTS_URL = "/vtop/finance/Payments"
PAYMENT_RECEIPT_URL = "/vtop/p2p/getReceiptsApplno"
PRINT_PAYMENT_RECEIPT_URL = "/vtop/finance/dupReceiptNewP2P"
VIRTUAL_ACCOUNT_URL = "/vtop/admissions/studentVirtualAccountNo"

# Curriculum URL
CURRICULUM_URL = "/vtop/academics/common/Curriculum"

# Time Table URL
TIME_TABLE_URL = "/vtop/academics/common/StudentTimeTable"
GET_TIME_TABLE_URL = "/vtop/processViewTimeTable"

# Exam Schedule URL
EXAM_SCHEDULE_URL = "/vtop/examinations/StudExamSchedule"
GET_EXAM_SCHEDULE_URL = "/vtop/examinations/doSearchExamScheduleForStudent"


# Attendance URL
ATTENDANCE_URL = "/vtop/academics/common/StudentAttendance"
VIEW_ATTENDANCE_URL = "/vtop/processViewStudentAttendance"
VIEW_ATTENDANCE_DETAIL_URL = "/vtop/processViewAttendanceDetail"
# Capstone/SDP attendance, reached from a button on the attendance page.
SDP_ATTENDANCE_URL = "/vtop/processSdpAttendance"

# Course Page URL
COURSE_PAGE_URL = "/vtop/academics/common/StudentCoursePage"

# Makrs URL
MARKS_URL = "/vtop/examinations/StudentMarkView"
VIEW_MARKS_URL = "/vtop/examinations/doStudentMarkView"

# Grades URL
GRADE_HISTORY_URL = "/vtop/examinations/examGradeView/StudentGradeHistory"


# Weekend Outing URL
WEEKEND_OUTING_URL = "/vtop/hostel/StudentWeekendOuting"
SAVE_WEEKEND_OUTING_URL = "/vtop/hostel/saveOutingForm"
EDIT_WEEKEND_OUTING_FORM = "/vtop/hostel/updateBookingInfo"
DELETE_WEEKEND_OUTING_FORM = "/vtop/hostel/deleteBookingInfo"


# General Outing URL
GENERAL_OUTING_URL = "/vtop/hostel/StudentGeneralOuting"
SAVE_GENERAL_OUTING_URL = "/vtop/hostel/saveGeneralOutingForm"
EDIT_GENRAL_OUTING_URL = "/vtop/hostel/updateGeneralOutingInfo"
DELETE_GENERAL_OUTING_URL = "/vtop/hostel/deleteGeneralOutingInfo"


# Hostel counselling URL.
#
# This was called NCGPA_RANK_URL, which it never was. The page serves hostel
# counselling slot booking: application number, blocks, floors, room
# preference, with getHostelBlocks / getFloorsByRoomType / getRoomsByFloorID /
# getRoomPreference behind it.
HOSTEL_COUNSELLING_URL = "/vtop/hostels/counsellingSlotTimings1"

# Profile image path
PFP_PATH = "/vtop/users/image/?id="

# Faculty URL
FACULTY_SEARCH_URL = "/vtop/hrms/EmployeeSearchForStudent"
FACULTY_DETAIL_URL = "/vtop/hrms/EmployeeSearch1ForStudent"

# Digital Assignment URL
DIGITAL_ASSIGNMENT_URL = "/vtop/examinations/doDigitalAssignment"
PROCESS_DIGITAL_ASSIGNMENT_URL = "/vtop/examinations/processDigitalAssignment"
PROCESS_DA_UPLOAD_URL = "/vtop/examinations/processDigitalAssignmentUpload"
DA_UPLOAD_URL = "/vtop/examinations/doDAssignmentUploadMethod"
DA_OTP_UPLOAD_URL = "/vtop/examinations/doDAssignmentOtpUpload"

# Outing download URL
DOWNLOAD_LEAVE_PASS_URL = "/vtop/hostel/downloadLeavePass"
DOWNLOAD_OUTING_FORM_URL = "/vtop/hostel/downloadOutingForm"

# Course Page URLs
GET_COURSE_FOR_COURSE_PAGE_URL = "/vtop/getCourseForCoursePage"
GET_SLOT_FOR_COURSE_PAGE_URL = "/vtop/getSlotIdForCoursePage"
VIEW_COURSE_DETAIL_URL = "/vtop/processViewStudentCourseDetail"
COURSE_PLAN_EXCEL_URL = "/vtop/academics/common/CoursePlanExcelDownload"

# Grade View URLs
GRADE_VIEW_URL = "/vtop/examinations/examGradeView/StudentGradeView"
DO_GRADE_VIEW_URL = "/vtop/examinations/examGradeView/doStudentGradeView"
GRADE_VIEW_DETAIL_URL = "/vtop/examinations/examGradeView/getGradeViewDetails"

# Academic calendar URLs.
#
# The page itself lives under academics/common, but its AJAX calls use relative
# urls, which the browser resolves against /vtop/content — so the endpoints sit
# at /vtop/ directly, not under academics/common.
CALENDAR_PREVIEW_URL = "/vtop/academics/common/CalendarPreview"
CALENDAR_CLASS_GROUPS_URL = "/vtop/getDateForSemesterPreview"
CALENDAR_MONTHS_URL = "/vtop/getListForSemester"
VIEW_CALENDAR_URL = "/vtop/processViewCalendar"
