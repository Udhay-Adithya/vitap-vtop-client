from bs4 import BeautifulSoup


def is_otp_required(html: str) -> bool:
    """
    Checks whether VTOP is asking for a login OTP.

    VTOP serves a form with id="securityOtpForm" when it wants the login to be
    confirmed with an OTP. This shows up either on the login error page or
    inlined into the login page itself, so callers should check both responses.

    Args:
        html (str): The HTML content returned from the login POST.

    Returns:
        bool: True if the OTP form is present, otherwise False.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        return soup.find("form", id="securityOtpForm") is not None
    except Exception as e:
        print(f"Warning: Error while checking for the login OTP form: {e}")
        return False
