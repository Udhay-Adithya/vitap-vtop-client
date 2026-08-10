import re
from typing import List

from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.payments.model.payment_receipt_model import PaymentReceipt

# The receipt number for the duplicate receipt download, e.g.
# doDuplicateReceipt('78323/27/AMR').
_RECEIPT_NO_RE = re.compile(r"doDuplicateReceipt\('([^']*)'\)")


def _header_index(header_row) -> dict[str, int]:
    """Maps upper cased header labels to their column positions."""
    cells = header_row.find_all(["td", "th"])
    return {cell.get_text(strip=True).upper(): i for i, cell in enumerate(cells)}


def parse_payment_receipts(html: str) -> List[PaymentReceipt]:
    """
    Parses the paid receipts table.

    Columns are located by header label rather than fixed position, because
    VTOP has reordered and inserted columns here over time (invoice number,
    fee group and fee subgroup now sit between the receipt number and the
    amount). Positional fallbacks keep it working if the headers change.

    The receipt number needed for the download lives in the row's view button,
    which is found by its handler rather than a fixed cell. Rows without such a
    button (totals or empty state rows) are skipped rather than treated as an
    error.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        all_rows = soup.find_all("tr")
        if not all_rows:
            return []

        headers = _header_index(all_rows[0])
        i_receipt = headers.get("RECEIPT NUMBER", 0)
        i_date = headers.get("DATE", 1)
        i_amount = headers.get("AMOUNT", 2)
        i_campus = headers.get("CAMPUS CODE", 3)

        def cell(cols, index: int) -> str:
            return cols[index].get_text(strip=True) if index < len(cols) else ""

        payments: List[PaymentReceipt] = []
        for row in all_rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            button = row.find(
                "button", onclick=re.compile("doDuplicateReceipt")
            )
            if button is None:
                # Not a receipt row (totals, empty state, etc.).
                continue

            match = _RECEIPT_NO_RE.search(button.get("onclick", ""))
            receipt_no = match.group(1) if match else ""

            payments.append(
                PaymentReceipt(
                    receipt_number=cell(cols, i_receipt),
                    date=cell(cols, i_date),
                    amount=cell(cols, i_amount),
                    campus_code=cell(cols, i_campus),
                    payment_status="Paid",
                    receipt_no=receipt_no,
                )
            )

        return payments

    except Exception as e:
        raise VtopParsingError(f"Failed to parse payment receipts: {e}") from e
