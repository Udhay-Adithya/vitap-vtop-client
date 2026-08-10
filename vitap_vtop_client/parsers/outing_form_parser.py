from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.outing.model.outing_info_model import OutingInfoModel

# Maps the form input ids VTOP renders to the model fields.
_FIELD_BY_INPUT_ID = {
    "regNo": "registration_number",
    "name": "name",
    "applicationNo": "application_no",
    "gender": "gender",
    "hostelBlock": "hostel_block",
    "roomNo": "room_number",
    "parentContactNumber": "parent_contact_number",
}


def parse_outing_form(html_content: str) -> OutingInfoModel:
    """
    Reads the pre-filled student details out of an outing form.

    Only the registration number is required; every other field is optional
    because VTOP does not render them all on every form. The general outing
    form, for instance, has no parentContactNumber input, and the weekend form
    renders nothing until the student is inside the eligibility window. Missing
    fields default to an empty string rather than raising, matching the
    lib_vtop rust crate.

    Args:
        html_content (str): The HTML of the outing form page.

    Returns:
        OutingInfoModel: The student details, with absent fields left empty.

    Raises:
        VtopParsingError: If the registration number is absent, which means the
            form did not render (e.g. the weekend form outside its window).
    """
    try:
        soup = BeautifulSoup(html_content, "lxml")
        values = {field: "" for field in _FIELD_BY_INPUT_ID.values()}

        for input_id, field in _FIELD_BY_INPUT_ID.items():
            element = soup.find("input", id=input_id)
            if element is not None:
                values[field] = element.get("value") or ""

        if not values["registration_number"]:
            raise VtopParsingError(
                "Outing form did not render a registration number. The weekend "
                "outing form is only available within its eligibility window "
                "(Tuesday to Friday); outside it, no form is served."
            )

        return OutingInfoModel(**values)

    except VtopParsingError:
        raise
    except Exception as e:
        raise VtopParsingError(
            f"Error parsing outing form information: {e}"
        ) from e
