from pydantic import BaseModel


class AttendanceModel(BaseModel):
    class_number: str
    course_code: str
    course_name: str
    course_type: str
    # Short code such as TH, ETH or ELA, needed to request attendance detail.
    course_type_code: str
    course_slot: str
    faculty: str
    attended_classes: str
    total_classes: str
    attendance_percentage: str
    attendance_between_percentage: str
    debar_status: str
    course_id: str


class AttendanceDetailModel(BaseModel):
    serial: str
    date: str
    slot: str
    day_time: str
    status: str
    remark: str
