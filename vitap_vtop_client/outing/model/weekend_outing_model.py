from typing import List
from pydantic import BaseModel, RootModel


class WeekendOutingRequest(BaseModel):
    serial: str = ""
    registration_number: str
    hostel_block: str
    room_number: str
    place_of_visit: str
    purpose_of_visit: str
    time: str
    contact_number: str
    parent_contact_number: str
    date: str
    booking_id: str
    action: str
    status: str
    # True when the request is accepted and VTOP offers a form download.
    can_download: bool = False


class WeekendOutingModel(RootModel):
    root: List[WeekendOutingRequest]
