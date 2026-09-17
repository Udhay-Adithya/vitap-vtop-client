Authentication
==============

Logging in is explicit and can take two steps. This is the single biggest
constraint the library puts on your design, so it is worth understanding before
you build around it.

The OTP gate
------------

VTOP asks for a one-time password after a period of inactivity, or when the
login comes from an IP address it has not seen. A deployed server is a new IP
address by definition, so this is not an edge case.

.. code-block:: python

   from vitap_vtop_client.exceptions import VtopLoginOtpRequiredError

   try:
       await client.login()
   except VtopLoginOtpRequiredError:
       otp = input("OTP sent to your registered email: ")
       await client.verify_login_otp(otp)

If the OTP expires before the user submits it, call
:meth:`~vitap_vtop_client.client.VtopClient.resend_login_otp` rather than
starting the login again.

:attr:`~vitap_vtop_client.client.VtopClient.otp_pending` reports whether a
challenge is outstanding.

Why it will not retry for you
-----------------------------

While an OTP is pending, ``_ensure_logged_in`` refuses to retry the login. A
silent retry would invalidate the OTP VTOP has already mailed to the student,
so the user would be typing a code that can no longer work.

For the same reason, never loop on a failed login. Repeated failures can lock
a VTOP account.

What this means for a web service
---------------------------------

An OTP challenge is raised during one request and answered during another. A
service that builds a client per request loses the pending state in between,
and can never complete the login.

Use :doc:`sessions` for this. Log in once, export the session, and rebuild a
client from it on later requests.

Captcha
-------

Solved locally by a small bundled model. Nothing to configure. VTOP sometimes
serves a page with no captcha image at all, so the fetch retries; if it never
arrives the login attempt restarts, bounded by ``captcha_retries`` and
``max_login_retries``.
