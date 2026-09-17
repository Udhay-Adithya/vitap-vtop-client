from bs4 import BeautifulSoup
from vitap_vtop_client.exceptions import VtopParsingError
from vitap_vtop_client.timetable.model import TimetableModel

# TODO: Use pandas to parse the timetable
# Current implementation is very sensitive to changes


def parse_timeslots(header_rows):
    """Parse timeslots from timetable header rows."""
    if len(header_rows) < 4:
        raise VtopParsingError("Insufficient header rows for timeslot parsing")

    # Process THEORY timeslots (first two rows)
    theory_starts = [
        td.get_text(strip=True) for td in header_rows[0].find_all("td")[2:]
    ]
    theory_ends = [td.get_text(strip=True) for td in header_rows[1].find_all("td")[1:]]
    theory_ends = theory_ends[: len(theory_starts)]  # Ensure equal length

    # Process LAB timeslots (next two rows)
    lab_starts = [td.get_text(strip=True) for td in header_rows[2].find_all("td")[2:]]
    lab_ends = [td.get_text(strip=True) for td in header_rows[3].find_all("td")[1:]]
    lab_ends = lab_ends[: len(lab_starts)]  # Ensure equal length

    # Combine start and end times
    theory_timings = [
        "Lunch" if start == "Lunch" and end == "Lunch" else f"{start} - {end}"
        for start, end in zip(theory_starts, theory_ends)
    ]

    lab_timings = [
        "Lunch" if start == "Lunch" and end == "Lunch" else f"{start} - {end}"
        for start, end in zip(lab_starts, lab_ends)
    ]

    return theory_timings, lab_timings


def get_course_info(html: str) -> list:
    """
    Parses the HTML content of a timetable table and extracts timetable details
    for each day into TimetableModel.

    Args:
        html (str): The raw HTML string containing the  timetable table.

    Returns:
        TimetableModel: A list of days, each representing the course schedule for that particualr day.

    Raises:
        VtopParsingError: When failed to parse timetable data(usually due to unexpected html format).
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        courses_list = []

        for row in rows:
            cells = row.find_all("td")
            if cells and len(cells) >= 10:
                try:
                    course_p = cells[2].find("p")
                    if course_p is not None:
                        course = course_p.get_text().strip()
                        course_code, course_name = course.split(" - ", 1)

                        venue = "N/A"
                        slot = "N/A"
                        venue_p = cells[7].find_all("p")
                        if venue_p:
                            slot = (venue_p[0]).get_text().strip()
                            venue = (venue_p[1]).get_text().strip()

                        faculty = "N/A"
                        faculty_p = cells[8].find_all("p")
                        if faculty_p:
                            faculty = (faculty_p[0]).get_text().split("-")[0]

                        courses_list.append(
                            {
                                str(course_code): {
                                    "course_name": course_name,
                                    "venue": venue,
                                    "slot": slot,
                                    "faculty": faculty,
                                }
                            }
                        )
                except Exception:
                    continue
        return courses_list
    except Exception as e:
        raise VtopParsingError(f"Error parsing course information: {e}")


def update_timetable_with_course_info(
    timetable_data: dict[str, list], courses_list: list
) -> TimetableModel:
    try:
        for day in timetable_data:
            for slot_idx in range(len(timetable_data[day])):
                slot_entry = timetable_data[day][slot_idx]
                # Extract timeslot and course info from the dictionary
                time_slot = slot_entry["time"]
                course_info_str = slot_entry["course_info"]

                # Parse course_info_str to get code, venue, and type
                parts = course_info_str.split("-")
                if len(parts) < 5:
                    # Create a basic course entry for invalid entries
                    timetable_data[day][slot_idx] = {
                        "course_name": "Unknown",
                        "slot": "N/A",
                        "venue": "N/A",
                        "faculty": "N/A",
                        "course_code": "N/A",
                        "course_type": "N/A",
                        "time": time_slot,
                    }
                    continue

                course_code = parts[1].strip()
                course_venue = f"{parts[3].strip()}-{parts[4].strip()}"
                course_type = parts[2].strip()

                # Find matching course in courses_list
                course_found = False
                for course in courses_list:
                    if course_code in course:
                        course_data = course[course_code]
                        # Check if venue matches
                        venue_parts = course_data["venue"].split("-")
                        if len(venue_parts) < 2:
                            continue
                        formatted_venue = f"{venue_parts[0]}-{venue_parts[1]}"
                        if course_venue == formatted_venue:
                            # Create new Course dict with time included
                            new_course = {
                                "course_name": course_data["course_name"],
                                "slot": course_data["slot"],
                                "venue": course_data["venue"],
                                "faculty": course_data["faculty"],
                                "course_code": course_code,
                                "course_type": course_type,
                                "time": time_slot,
                            }
                            # Replace the dictionary entry with the new Course
                            timetable_data[day][slot_idx] = new_course
                            course_found = True
                            break

                # If no matching course found, create a basic entry
                if not course_found:
                    timetable_data[day][slot_idx] = {
                        "course_name": "Unknown",
                        "slot": "N/A",
                        "venue": course_venue,
                        "faculty": "N/A",
                        "course_code": course_code,
                        "course_type": course_type,
                        "time": time_slot,
                    }

        return TimetableModel(**timetable_data)
    except Exception as e:
        raise VtopParsingError(f"Error updating timetable: {e}")


def parse_time_table(html: str) -> TimetableModel:
    # Initialize with all days having empty schedules
    timetable_data = {
        day: []
        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    }

    try:
        soup = BeautifulSoup(html, "html.parser")
        time_table = soup.find(id="timeTableStyle")
        if not time_table:
            return TimetableModel()

        all_rows = time_table.find_all("tr")
        if len(all_rows) < 4:
            return TimetableModel()

        # Parse timeslots from first 4 header rows
        theory_timings, lab_timings = parse_timeslots(all_rows[:4])
        data_rows = all_rows[4:]

        # Day mapping from abbreviations to full names
        day_mapping = {
            "MON": "Monday",
            "TUE": "Tuesday",
            "WED": "Wednesday",
            "THU": "Thursday",
            "FRI": "Friday",
            "SAT": "Saturday",
            "SUN": "Sunday",
        }

        # Process each pair of rows (THEORY + LAB)
        i = 0
        while i < len(data_rows):
            # Extract day name from the first cell of the THEORY row
            day_cell = data_rows[i].find("td")
            if not day_cell:
                i += 1
                continue

            day_abbr = day_cell.get_text(strip=True)
            day_name = day_mapping.get(day_abbr, day_abbr)

            # Process THEORY row
            theory_cells = data_rows[i].find_all("td")
            # Skip first two cells (day and "THEORY" label)
            theory_slots = (
                [
                    cell.get_text(strip=True)
                    for cell in theory_cells[2 : 2 + len(theory_timings)]
                ]
                if len(theory_cells) > 2
                else []
            )

            # Process LAB row if available
            lab_slots = []
            if i + 1 < len(data_rows):
                lab_cells = data_rows[i + 1].find_all("td")
                # Skip first cell ("LAB" label)
                lab_slots = (
                    [
                        cell.get_text(strip=True)
                        for cell in lab_cells[1 : 1 + len(lab_timings)]
                    ]
                    if len(lab_cells) > 1
                    else []
                )

            # Add THEORY slots to timetable
            for slot_idx, course_info in enumerate(theory_slots):
                if course_info not in {"-", "Lunch", "CLUBS/ECS", "ECS/CLUBS"}:
                    timetable_data[day_name].append(
                        {"time": theory_timings[slot_idx], "course_info": course_info}
                    )

            # Add LAB slots to timetable
            for slot_idx, course_info in enumerate(lab_slots):
                if course_info not in {"-", "Lunch"}:
                    timetable_data[day_name].append(
                        {"time": lab_timings[slot_idx], "course_info": course_info}
                    )

            # Move to next day pair (THEORY + LAB rows)
            i += 2

        # Cleanup: Remove invalid entries
        for day in timetable_data:
            timetable_data[day] = [
                session
                for session in timetable_data[day]
                if len(session["course_info"]) >= 8
            ]

        courses_list = get_course_info(html)
        return update_timetable_with_course_info(timetable_data, courses_list)

    except Exception as e:
        raise VtopParsingError(f"Failed to parse timetable: {e}")
