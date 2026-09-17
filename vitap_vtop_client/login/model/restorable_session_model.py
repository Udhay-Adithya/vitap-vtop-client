from pydantic import BaseModel


class RestorableSession(BaseModel):
    """Everything needed to rebuild a VtopClient in another process.

    VTOP holds the session server side against the JSESSIONID cookie, so these
    four values are enough to keep using an authenticated session without
    logging in again. Treat them as credentials: anyone holding them can read
    the student's records for as long as VTOP keeps the session alive.
    """

    registration_number: str
    cookie: str
    csrf_token: str
    # Advisory. VTOP was not observed to require a reused session to match the
    # agent that created it, but keeping one identity costs nothing.
    user_agent: str
