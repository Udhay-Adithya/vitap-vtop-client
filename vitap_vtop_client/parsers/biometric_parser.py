from bs4 import BeautifulSoup

from vitap_vtop_client.biometric.model.biometric_model import BiometricModel
from vitap_vtop_client.exceptions.exception import VtopParsingError


def _cell_text(cell) -> str:
    return cell.get_text(strip=True).replace("\t", "").replace("\n", "")


def parse_biometric(html: str) -> list[BiometricModel]:
    """
    Parses the biometric log table into one record per punch.

    Args:
        html (str): The raw HTML string containing the biometric log table.

    Returns:
        list[BiometricModel]: One entry per biometric punch.

    Raises:
        VtopParsingError: If parsing fails due to malformed or unexpected HTML.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        biometric_logs: list[BiometricModel] = []

        # Skip the header row.
        for row in soup.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            biometric_logs.append(
                BiometricModel(
                    serial=_cell_text(cells[0]),
                    date=_cell_text(cells[1]),
                    in_time=_cell_text(cells[2]),
                    location=_cell_text(cells[3]),
                )
            )

        return biometric_logs

    except Exception as e:
        raise VtopParsingError(f"Failed to parse biometric data: {e}") from e
