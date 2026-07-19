from bs4 import BeautifulSoup

_OUTCOME_WORDS = ("Successfully", "Applied", "Deleted")
_FAILURE_WORDS = ("Error", "Failed")

# Boilerplate shown on the outing form that is not an error message.
_FORM_NOTICES = ("disciplinary measures", "logs will be retained")


def parse_outing_response(html: str) -> str:
    """
    Reads the outcome of an outing submission or deletion.

    VTOP has no consistent response shape here. Weekend outings return a
    coloured span, general outings return a SweetAlert modal, and a failed
    submission may simply re-render the form page. Each of those is checked in
    turn.

    Args:
        html (str): The raw HTML returned by the outing endpoint.

    Returns:
        str: The message from VTOP, prefixed with "Error: " when the response
            indicates a failure, or a description of why it could not be read.
    """
    soup = BeautifulSoup(html, "lxml")

    # Explicit error styling wins over everything else.
    for span in soup.select(
        "span[style*='color: red'], span[style*='color:red'], .error, .alert-danger"
    ):
        text = span.get_text(strip=True)
        if text:
            return f"Error: {text}"

    # Weekend outing: a green span carrying the outcome.
    for span in soup.select(
        "span.col-md-12[style*='color: green'], span.col-md-12[style*='color:green']"
    ):
        text = span.get_text(strip=True)
        if text and any(word in text for word in _OUTCOME_WORDS):
            return text

    # General outing: a SweetAlert modal heading.
    for heading in soup.select("div.sweet-alert h2"):
        text = heading.get_text(strip=True)
        if text:
            return text

    # Fall back to any heading that reads like an outcome.
    for heading in soup.find_all("h2"):
        text = heading.get_text(strip=True)
        if text and any(
            word in text for word in _OUTCOME_WORDS + _FAILURE_WORDS
        ):
            return text

    # The form page coming back usually means the submission was rejected.
    if "outingForm" in html and "Weekend Outing Request" in html:
        for span in soup.select(
            "span.col-sm-12[style*='color'], span.col-md-12[style*='color']"
        ):
            text = span.get_text(strip=True)
            if text and not any(notice in text for notice in _FORM_NOTICES):
                return f"Error: {text}"

        return (
            "Submission may have failed - form page was returned. "
            "Please check outing history to verify."
        )

    return (
        "Unable to parse response from server. "
        "Please check outing history to verify submission."
    )
