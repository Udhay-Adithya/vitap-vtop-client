from typing import List
from pydantic import BaseModel


class SemesterInfo(BaseModel):
    id: str
    name: str


class SemesterData(BaseModel):
    semesters: List[SemesterInfo] = []
    update_time: int
