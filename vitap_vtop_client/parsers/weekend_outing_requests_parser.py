from bs4 import BeautifulSoup
from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.outing.model.weekend_outing_model import (
    WeekendOutingModel,
    WeekendOutingRequest,
)


def parse_weekend_outing_requests(html: str) -> WeekendOutingModel:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="BookingRequests")
    requests = []

    try:
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                booking_id = cols[10].get_text().strip()
                status = (
                    cols[12].get_text().replace("\n", " ").replace("\t", "").strip()
                )

                request = WeekendOutingRequest(
                    serial=cols[0].get_text().strip(),
                    registration_number=cols[1].get_text().strip(),
                    hostel_block=cols[2].get_text().strip(),
                    room_number=cols[3].get_text().strip(),
                    place_of_visit=cols[4].get_text().strip(),
                    purpose_of_visit=cols[5].get_text().strip(),
                    time=cols[6].get_text().strip(),
                    contact_number=cols[7].get_text().strip(),
                    parent_contact_number=cols[8].get_text().strip(),
                    date=cols[9].get_text().strip(),
                    booking_id=booking_id,
                    action=cols[11].get_text().strip(),
                    status=status,
                    # VTOP only issues the outing form once the request is
                    # accepted, so the status has to be checked too.
                    can_download=bool(booking_id)
                    and status.lower().strip() == "outing request accepted",
                )
                requests.append(request)

        return WeekendOutingModel(root=requests)

    except Exception as e:
        print(f"Error parsing wekend outing requests: {e}")
        raise VtopParsingError(f"Error parsing wekend outing requests: {e}")
