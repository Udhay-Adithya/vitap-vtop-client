import httpx

from vitap_vtop_client.constants import (
    HEADERS,
    VTOP_RESEND_OTP_URL,
    VTOP_VALIDATE_OTP_URL,
)
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopLoginError,
    VtopLoginOtpExpiredError,
    VtopLoginOtpIncorrectError,
)
from vitap_vtop_client.login.model.logged_in_student_model import LoggedInStudent
from vitap_vtop_client.utils import find_csrf
from vitap_vtop_client.utils.find_registration_number import find_registration_number


async def verify_login_otp(
    client: httpx.AsyncClient,
    csrf_token: str,
    otp: str,
) -> LoggedInStudent:
    """
    Submits the login OTP to VTOP to finalise the session.

    On success VTOP responds with a redirect URL to the authenticated content
    page, which is then loaded to pick up the post-login CSRF token and the
    registration number.

    Args:
        client (httpx.AsyncClient): Async client carrying the pending session.
        csrf_token (str): CSRF token scraped from the OTP page.
        otp (str): The OTP entered by the user.

    Returns:
        LoggedInStudent: The registration number and post-login CSRF token.

    Raises:
        VtopLoginOtpIncorrectError: If VTOP reports the OTP as invalid.
        VtopLoginOtpExpiredError: If VTOP reports the OTP as expired.
        VtopLoginError: If verification fails for any other reason.
        VtopConnectionError: If a network-related issue occurs.
    """
    try:
        files = {
            "otpCode": (None, otp),
            "_csrf": (None, csrf_token),
        }
        response = await client.post(
            VTOP_VALIDATE_OTP_URL, files=files, headers=HEADERS
        )

        if response.status_code != 200:
            raise VtopLoginError(
                f"Failed to verify OTP. Server responded with status: {response.status_code}",
                status_code=response.status_code,
            )

        payload = response.json()
        status = payload.get("status", "STATUS_NOT_FOUND")
        message = payload.get("message", "MESSAGE_NOT_FOUND")

        if status == "INVALID":
            raise VtopLoginOtpIncorrectError(
                "Incorrect OTP entered for login. Please try again.", status_code=401
            )

        if status == "EXPIRED":
            raise VtopLoginOtpExpiredError(
                "OTP for login has expired. Please request a new OTP and try again.",
                status_code=401,
            )

        if status != "SUCCESS":
            raise VtopLoginError(f"{status}: {message}", status_code=401)

        redirect_url = payload.get("redirectUrl")
        if not redirect_url:
            raise VtopLoginError(
                "Redirect URL not found after OTP verification.", status_code=502
            )

        content_resp = await client.get(redirect_url, headers=HEADERS)

        registration_number = find_registration_number(content_resp.text)
        if not registration_number:
            raise VtopLoginError(
                "OTP was accepted but the registration number could not be read "
                "from the content page.",
                status_code=502,
            )
        post_login_csrf = find_csrf(content_resp.text)
        return LoggedInStudent(
            registration_number=registration_number,
            post_login_csrf_token=post_login_csrf,
        )

    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"OTP verification request failed: {e}",
            original_exception=e,
            status_code=502,
        )
    except VtopLoginError:
        raise
    except Exception as e:
        raise VtopLoginError(
            f"An unexpected error occurred during OTP verification: {e}"
        ) from e


async def resend_login_otp(client: httpx.AsyncClient, csrf_token: str) -> None:
    """
    Asks VTOP to send a fresh login OTP.

    Used when the previous OTP expired or never arrived.

    Args:
        client (httpx.AsyncClient): Async client carrying the pending session.
        csrf_token (str): CSRF token scraped from the OTP page.

    Raises:
        VtopLoginError: If VTOP declines to resend the OTP.
        VtopConnectionError: If a network-related issue occurs.
    """
    try:
        files = {"_csrf": (None, csrf_token)}
        response = await client.post(VTOP_RESEND_OTP_URL, files=files, headers=HEADERS)

        if response.status_code != 200:
            raise VtopLoginError(
                "Failed to request OTP. Please try again.",
                status_code=response.status_code,
            )

        payload = response.json()
        status = payload.get("status", "UNKNOWN_STATUS_FOR_RESEND_OTP")
        if status != "SUCCESS":
            message = payload.get(
                "message", "Failed to resend OTP from server side"
            )
            raise VtopLoginError(f"{status}: {message}", status_code=502)

    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"OTP resend request failed: {e}", original_exception=e, status_code=502
        )
    except VtopLoginError:
        raise
    except Exception as e:
        raise VtopLoginError(
            f"An unexpected error occurred while resending the OTP: {e}"
        ) from e
