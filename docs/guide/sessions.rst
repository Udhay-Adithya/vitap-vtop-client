Sessions
========

VTOP keeps the session on the server, keyed by a ``JSESSIONID`` cookie. A
client holding that cookie and the post-login CSRF token can make data requests
without authenticating at all.

That makes a session portable, which is what lets a caller avoid holding a live
client in memory.

Exporting and restoring
-----------------------

.. code-block:: python

   # once, wherever you can prompt for an OTP
   async with VtopClient("REGNO", "password") as client:
       await client.login()
       session = client.session          # RestorableSession

   # later, in another process, with no credentials
   client = VtopClient.restore(
       session.registration_number,
       session.cookie,
       session.csrf_token,
       user_agent=session.user_agent,
   )
   attendance = await client.get_attendance(sem_sub_id)

A restored client holds no password. If the session has expired it cannot log
back in, and raises :class:`~vitap_vtop_client.exceptions.exception.VtopSessionError`
saying so, rather than attempting a login it cannot complete.

Carrying an OTP challenge
-------------------------

An authenticated session is only half the problem. If VTOP interrupts the login
with an OTP, the challenge is raised while you are answering one request and the
OTP arrives on the next — by which point the client that raised it is gone.

A pending challenge carries the same way:

.. code-block:: python

   try:
       await client.login()
   except VtopLoginOtpRequiredError:
       challenge = client.otp_challenge     # hand this back to the caller

   # ... a later request, another process ...
   client = VtopClient.restore_otp_challenge(
       challenge.registration_number,
       challenge.cookie,
       challenge.csrf_token,
       user_agent=challenge.user_agent,
   )
   await client.verify_login_otp(otp)       # or client.resend_login_otp()
   session = client.session                 # now a full session

A restored challenge is deliberately **not** authenticated. Asking it for data
raises ``VtopSessionError`` telling you to answer the OTP first, so a
half-finished login cannot be mistaken for a usable one.

.. warning::

   An :class:`~vitap_vtop_client.login.model.otp_challenge_model.OtpChallenge`
   is a credential too. Credentials and captcha have already been accepted, so
   anyone holding one can finish the login as soon as they have the OTP.

.. warning::

   Treat the exported values as credentials. Anyone holding them can read the
   student's records for as long as VTOP keeps the session alive.

When a session dies
-------------------

An expired CSRF token does not redirect you to the login page. Spring's CSRF
filter refuses the request before it is routed, so Tomcat answers with its own
404. The client recognises this and raises ``VtopSessionError`` with a 401,
because the caller's problem is authentication rather than a missing page.

Two CSRF tokens
---------------

There is a pre-login token used to authenticate, and a different post-login
token that every data request needs. They are not interchangeable. The second
is on ``LoggedInStudent.post_login_csrf_token`` and is what
:attr:`~vitap_vtop_client.client.VtopClient.session` exports.

The User-Agent
--------------

Each client pins one User-Agent for the life of its session, so the session
presents a consistent identity. As of 2026-09-17 VTOP was **not** observed to
require that a reused session match the agent that created it — an exported
session was reused successfully from a completely different agent. Passing the
original value is advisory, not required.
