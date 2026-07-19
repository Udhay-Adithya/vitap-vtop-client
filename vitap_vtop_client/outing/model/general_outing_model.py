from typing import List
from pydantic import BaseModel, RootModel


class GeneralOutingRequest(BaseModel):
    serial: str = ""
    registration_number: str
    place_of_visit: str
    purpose_of_visit: str
    from_date: str
    from_time: str
    to_date: str
    to_time: str
    leave_id: str
    action: str
    status: str
    # True when VTOP offers a leave pass download for this request.
    can_download: bool = False


class GeneralOutingModel(RootModel):
    root: List[GeneralOutingRequest]
