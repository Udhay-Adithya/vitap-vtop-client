HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Connection": "close",
}

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
VIRTUAL_ACCOUNT_URL = "/vtop/admissions/studentVirtualAccountNo "

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


# NCGPA Rank URL
NCGPA_RANK_URL = "/vtop/hostels/counsellingSlotTimings1"

# Profile image path
PFP_PATH = "/vtop/users/image/?id="

# Semester Sub ID's
SemSubID = {
    "Summer Semester2 2024-25": "AP2024258",
    "Summer Semester1 2024-25": "AP2024257",
    "Long Semester 2024-25": "AP2024256",
    "Winter Semester 2024-25 Freshers": "AP2024255",
    "Winter Semester 2024-25": "AP2024254",
    "FALL SEM 2024-25 FRESHERS": "AP2024253",
    "FALL SEM 2024-25": "AP2024252",
    "Fall_Win_sem_2024-25": "AP20232413",
    "Regular Arrear 2023-24": "AP20232412",
    "Fast Track Fall 2024-25": "AP2024251",
    "Short Summer Semester2 2023-24": "AP2023249",
    "Fast Track Fall 2024-25": "AP2024251",
    "Long Summer Semester 2023-24": "AP20232410",
    "Short Summer Semester1 2023-24": "AP2023248",
    "WINTER SEM(2023-24) FRESHERS": "AP2023247",
    "WIN SEM (2023-24)": "AP2023246",
    "INTRA SEM (2023-24": "AP2023245",
    "Preference Purpose (2023-24": "AP2022233",
    "FALL SEM (2023-24) Freshers": "AP2023243",
    "FALL SEM (2023-24) Regular": "AP2023242",
    "FAST TRACK FALL II(2023-24)": "AP2023244",
    "SHORT SUMMER SEMESTER II (2022-23)": "AP20222310",
    "FAST TRACK FALL (2023-24": "AP2023241",
    "SHORT SUMMER SEMESTER I (2022-23)": "AP2022239",
    "LONG SUMMER SEMESTER (2022-23)": "AP2022238",
    "WIN SEM (2022-23) Freshers": "AP2022237",
    "WIN SEM (2022-23)": "AP2022236",
    "INTRA SEM (2022-23": "AP2022235",
    "FALL SEM (2022-23) Freshers": "AP2022234",
    "FALL SEM (2022-23)": "AP2022232",
    "FAST TRACK FALL (2022-23)": "AP2022231",
    "Short-Summer Semester 2021-22": "AP2021227",
    "Long-Summer Semester 2021-22": "AP2021228",
    "INTRA SEM (2021-22)": "AP2021229",
    "WIN SEM (2021-22) EAPCET": "AP2021226",
    "WIN SEM (2021-22)": "AP2021225",
    "FALL SEM (2021-22) EAPCET": "AP2021223",
    "FALL SEM (2021-22": "AP2021222",
    "SUMMER SEM1 (2020-21)": "AP2020217",
    "FAST TRACK FALL SEM (2021-22)": "AP2021221",
    "WIN SEM (2020-21)": "AP2020215",
    "INTRA SEM (2020-21)": "AP2020213",
    "FALL SEM (2020-21)": "AP2020211",
    "SUMMER SEM1 (2019-20)": "AP2019207",
    "WIN SEM  (2019-20)": "AP2019205",
    "FALL SEM (2019-20)": "AP2019201",
    "SUMMER SEM2 (2018-19)": "AP2018198",
    "SUMMER SEM1 (2018-19)": "AP2018197",
    "LONG SEM (2018-19)": "AP2018199",
    "WIN SEM (2018-19)": "AP2018195",
    "FALL SEM (2018-19)": "AP2018191",
    "SUMMER SEM2 (2017-18)": "AMR2018198",
    "SUMMER SEM1 (2017-18)": "AMR2018197",
    "WIN SEM (2017-18)": "AMR2017182",
    "FALL SEM (2017-18)": "AMR2017181",
    "TESTING": "AP20101101",
}
