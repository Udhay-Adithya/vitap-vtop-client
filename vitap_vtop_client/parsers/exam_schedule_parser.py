from bs4 import BeautifulSoup
from collections import defaultdict

from vitap_vtop_client.exam_schedule.model.exam_schedule_model import (
    ExamScheduleModel,
    ExamScheduleGroup,
    ExamEntry,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError


def parse_exam_schedule(html: str) -> ExamScheduleModel:
    try:
        soup = BeautifulSoup(html, "html.parser")
        schedule_table = soup.find("table")

        if not schedule_table:
            return ExamScheduleModel(root=[])

        rows = schedule_table.find_all("tr")
        exam_schedule = defaultdict(list)
        current_exam_type = None

        for row in rows:
            cells = row.find_all("td")
            values = [cell.text.strip() for cell in cells]

            if len(values) == 1:
                current_exam_type = values[0]
                continue
            elif len(values) < 13 or "S.No." in values:
                continue

            exam_entry = ExamEntry(
                serial_number=values[0],
                course_code=values[1],
                course_name=values[2],
                course_type=values[3],
                course_id=values[4],
                slot=values[5],
                exam_date=values[6],
                exam_session=values[7],
                reporting_time=values[8],
                exam_time=values[9],
                venue=values[10],
                seat_location=values[11],
                seat_number=values[12],
            )

            if current_exam_type:
                exam_schedule[current_exam_type].append(exam_entry)

        result = [
            ExamScheduleGroup(exam_type=exam_type, subjects=subjects)
            for exam_type, subjects in exam_schedule.items()
        ]

        return ExamScheduleModel(root=result)

    except Exception as e:
        print(f"Failed to parse exam schedule: {e}")
        raise VtopParsingError(f"Failed to parse exam schedule: {e}")
