from bs4 import BeautifulSoup

# Phrases that mark an outing outcome as OK or pending — not an error.
#
# VTOP styles the "Waiting for ... Approval" pending status in red, which a
# naive parser reads as an error (treating every red span as one).
_POSITIVE_PHRASES = ("successfully", "waiting for", "accepted")

# Boilerplate shown on the outing form that is not an error message.
_FORM_NOTICES = ("disciplinary measures", "logs will be retained")


def _is_positive_outcome(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _POSITIVE_PHRASES)


def parse_outing_response(html: str, page_reload_message: str) -> str:
    """
    Reads the outcome of an outing submission or deletion.

    VTOP no longer returns a distinct confirmation for these actions — the
    SweetAlert popups are commented out server side, and the save/delete
    handlers simply reload the outing page
    (`$("#main-section").html(response)`). So the response is the full outing
    page: the request form plus the `BookingRequests` table, whose status column
    carries per-request statuses ("Waiting for Mentor's Approval" in red,
    "Leave Request Accepted" in green). Those are not the result of the current
    action and must be ignored.

    Args:
        html (str): The raw HTML returned by the outing endpoint.
        page_reload_message (str): What to report when VTOP simply reloads the
            page, which is the normal successful outcome. The caller supplies
            it because the HTML cannot distinguish an apply from a delete.

    Returns:
        str: The message from VTOP, prefixed with "Error: " when the response
            indicates a genuine failure, or `page_reload_message` on success.
    """
    soup = BeautifulSoup(html, "lxml")

    # The status spans inside the requests table are per-request statuses, not
    # the result of this action. Collect them so they can be skipped below.
    requests_table = soup.find(id="BookingRequests")
    table_spans = (
        set(id(span) for span in requests_table.find_all("span"))
        if requests_table is not None
        else set()
    )

    def outside_table(element) -> bool:
        return id(element) not in table_spans

    # 1. An explicit success message shown outside the requests list: a
    #    SweetAlert heading, or a green form level span (older VTOP responses,
    #    and any delete popup that is still enabled).
    for heading in soup.select("div.sweet-alert h2"):
        text = heading.get_text(strip=True)
        if text:
            return text

    for span in soup.select(
        "span[style*='color: green'], span[style*='color:green']"
    ):
        text = span.get_text(strip=True)
        if text and outside_table(span) and _is_positive_outcome(text):
            return text

    # 2. A genuine form level error: a red / alert message OUTSIDE the requests
    #    list that is not itself a positive outcome and not boilerplate. The
    #    pending "Waiting for ... Approval" status lives inside the table and is
    #    skipped, so it is never reported as an error.
    for element in soup.select(
        ".alert-danger, .error, span[style*='color: red'], span[style*='color:red']"
    ):
        text = element.get_text(strip=True)
        if not text or not outside_table(element):
            continue
        if _is_positive_outcome(text):
            continue
        if any(notice in text for notice in _FORM_NOTICES):
            continue
        return f"Error: {text}"

    # 3. The requests list came back with no form level message — the page
    #    reloaded, which is the normal successful outcome.
    if requests_table is not None or "BookingRequests" in html:
        return page_reload_message

    # 3b. Only the bare form came back (no requests list, no message). This is
    #     abnormal and usually means the submission did not go through.
    if "outingForm" in html:
        return (
            "Submission may have failed - the form page was returned. "
            "Please check outing history to verify."
        )

    # 4. Nothing recognisable.
    return (
        "Unable to parse response from server. "
        "Please check outing history to verify submission."
    )
