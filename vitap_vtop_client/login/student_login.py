import httpx
from vitap_vtop_client.constants import (
    VTOP_LOGIN_URL,
    VTOP_CONTENT_URL,
    HEADERS,
)
from vitap_vtop_client.exceptions.exception import (
    VtopCaptchaSolvingError,
    VtopConnectionError,
    VtopLoginError,
    VtopLoginOtpRequiredError,
)
from vitap_vtop_client.login.model.logged_in_student_model import LoggedInStudent
from vitap_vtop_client.utils import find_login_response
from vitap_vtop_client.utils import find_csrf
from vitap_vtop_client.utils.is_otp_required import is_otp_required
from vitap_vtop_client.utils.find_registration_number import find_registration_number


# TODO: Implement retry mechanism for Captch Failures
async def student_login(
    client: httpx.AsyncClient,
    csrf_token: str,
    registration_number: str,
    password: str,
    captcha_value: str,
) -> LoggedInStudent:
    """
    Attempts to log in to the VTOP system using provided credentials and captcha.

    Args:
        client (httpx.AsyncClient): Async client object for making HTTP requests.
        csrf_token (str): Cross-Site Request Forgery token required for the login request (from pre-login).
        registration_number (str): Student Registration Number for logging in.
        password (str): VTOP Password for logging in.
        captcha_value (str): Value of the CAPTCHA image solved by the solver.

    Returns:
        LoggedInStudent: The registration number and post-login CSRF token.

    Raises:
        VtopCaptchaSolvingError: If the submitted captcha answer was rejected.
        VtopLoginOtpRequiredError: If VTOP requires an OTP to finish the login.
            Credentials and captcha were accepted; the caller must collect the
            OTP and call `verify_login_otp`.
        VtopLoginError: If the credentials are rejected or login otherwise fails.
        VtopConnectionError: If a network-related issue occurs during the POST.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "username": registration_number,
            "password": password,
            "captchaStr": captcha_value,
        }
        response = await client.post(VTOP_LOGIN_URL, data=data, headers=HEADERS)

        if "error" in str(response.url):
            if "Invalid Captcha" in response.text:
                raise VtopCaptchaSolvingError("Invalid Captcha", status_code=401)

            # VTOP may serve the OTP form on the error page even though the
            # credentials and captcha were accepted.
            if is_otp_required(response.text):
                raise VtopLoginOtpRequiredError(
                    "OTP verification is required to complete the login.",
                    status_code=401,
                    csrf_token=find_csrf(response.text),
                )

            error_message = (
                find_login_response.login_error_identifier(response.text)
                or "Unknown login error"
            )
            print(f"Login Credential Error: {error_message}")
            raise VtopLoginError(f"{error_message}", status_code=401)

        # The OTP form is sometimes inlined into the login page itself rather
        # than served from the error route.
        if is_otp_required(response.text):
            raise VtopLoginOtpRequiredError(
                "OTP verification is required to complete the login.",
                status_code=401,
                csrf_token=find_csrf(response.text),
            )

        print(
            f"Login successful for user {registration_number[:5]}****. Redirected to content page."
        )
        # After successful login, we need to get the new CSRF token from the content page
        # for subsequent requests.
        content_resp = await client.get(VTOP_CONTENT_URL, headers=HEADERS)

        registration_number = find_registration_number(content_resp.text)
        if not registration_number:
            raise VtopLoginError(
                "Login appeared to succeed but the registration number could "
                "not be read from the content page.",
                status_code=502,
            )
        print(f"registration number is {registration_number[:5]}****")
        post_login_csrf = find_csrf(content_resp.text)
        logged_in_student = {
            "registration_number": registration_number,
            "post_login_csrf_token": post_login_csrf,
        }
        return LoggedInStudent(**logged_in_student)

    except httpx.RequestError as e:
        print(f"Login POST request failed: Network Error {e}")
        raise VtopConnectionError(
            f"Login request failed: {e}", original_exception=e, status_code=502
        )
    except VtopLoginError as e:
        raise e

    except Exception as e:
        print(f"An unexpected error occurred during login process: {e}")
        raise VtopLoginError(f"An unexpected error occurred during login: {e}") from e
