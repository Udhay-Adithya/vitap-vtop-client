from bs4 import BeautifulSoup
from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.outing.model.general_outing_model import (
    GeneralOutingRequest,
    GeneralOutingModel,
)


def parse_general_outing_requests(html: str) -> GeneralOutingModel:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="BookingRequests")
    requests = []

    try:
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")

                leave_id = find_leave_id(cols[10])

                request = GeneralOutingRequest(
                    serial=cols[0].get_text().strip(),
                    registration_number=cols[1].get_text().strip(),
                    place_of_visit=cols[2].get_text().strip(),
                    purpose_of_visit=cols[3].get_text().strip(),
                    from_date=cols[4].get_text().strip(),
                    from_time=cols[5].get_text().strip(),
                    to_date=cols[6].get_text().strip(),
                    to_time=cols[7].get_text().strip(),
                    action=cols[8].get_text().strip(),
                    status=cols[9]
                    .get_text()
                    .replace("\n", " ")
                    .replace("\t", "")
                    .strip(),
                    leave_id=leave_id,
                    can_download=bool(leave_id),
                )
                requests.append(request)

        return GeneralOutingModel(root=requests)

    except Exception as e:
        print(f"Error parsing general outing requests: {e}")
        raise VtopParsingError(f"Error parsing general outing requests: {e}")


def find_leave_id(col_10):
    # Find the <a> tag with data-url attribute
    a_tag = col_10.find("a", {"data-url": True})

    if a_tag:
        data_url = a_tag.get("data-url")
        return data_url.split("/")[-1]  # Get last segment of URL
    # No download link means there is no leave pass to fetch. can_download
    # carries that signal, so return an empty id rather than a sentinel.
    return ""
