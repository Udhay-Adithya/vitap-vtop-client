from pydantic import BaseModel


class OtpChallenge(BaseModel):
    """A login VTOP has interrupted for an OTP, in a form that can be carried.

    Credentials and captcha have already been accepted at this point; only the
    OTP is outstanding. Handing these values to another process lets it finish
    the login with `VtopClient.restore_otp_challenge`, which is what a web
    service needs: the challenge is raised while answering one request and the
    OTP arrives on the next.

    Treat them as credentials. Anyone holding them can complete the login as
    soon as they have the OTP.
    """

    registration_number: str
    cookie: str
    # The CSRF token scraped from the OTP page, which must be submitted
    # alongside the OTP. VtopLoginOtpRequiredError carries the same value.
    csrf_token: str
    # Advisory, as with RestorableSession: VTOP was not observed to require a
    # reused session to match the agent that created it.
    user_agent: str
