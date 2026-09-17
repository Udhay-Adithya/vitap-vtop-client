# VTOP's catch-all rejection. It is served with HTTP 200 and a body, so
# raise_for_status() passes and the fragment reaches the parser, which then
# fails on markup it cannot recognise.
MENU_UNAVAILABLE_MARKER = "This menu is not available at present"


def is_menu_unavailable(html: str) -> bool:
    """
    Checks whether VTOP rejected the request with its generic modal.

    VTOP answers a rejected request with a ~1KB fragment containing
    "This menu is not available at present!!!" and an HTTP 200. Two different
    causes produce a byte-identical body, and the response gives no way to tell
    them apart:

      * the request shape was wrong -- a data endpoint wants `_csrf`,
        `authorizedID` and `x`, and rejects the `verifyMenu`/`nocache` body the
        page shells take
      * the portal really has turned that menu off

    A bad parameter is *not* one of them. An unknown or missing `semesterSubId`
    returns a normal, empty table instead, which is its own problem and not one
    this function can see.

    Args:
        html (str): The HTML content returned by VTOP.

    Returns:
        bool: True if VTOP returned the rejection modal, otherwise False.
    """
    return MENU_UNAVAILABLE_MARKER in html
