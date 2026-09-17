Error handling
==============

Every error inherits from
:class:`~vitap_vtop_client.exceptions.exception.VitapVtopClientError`, so you
can catch that one type and inspect ``status_code`` if you are mapping onto
HTTP.

.. code-block:: python

   from vitap_vtop_client.exceptions import VitapVtopClientError

   try:
       attendance = await client.get_attendance(sem_sub_id)
   except VitapVtopClientError as e:
       print(type(e).__name__, e.status_code, e)

What each one means
-------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Exception
     - Meaning
   * - ``VtopLoginError``
     - Credentials rejected. Its subclasses cover captcha and CSRF failures.
   * - ``VtopLoginOtpRequiredError``
     - Credentials accepted; VTOP wants an OTP. Carries the page's CSRF token.
   * - ``VtopLoginOtpIncorrectError`` / ``...ExpiredError``
     - The submitted OTP was wrong, or is no longer valid.
   * - ``VtopSessionError``
     - The session or CSRF token is dead, or an OTP is pending. Log in again.
   * - ``VtopMenuUnavailableError``
     - VTOP refused to answer. See below.
   * - ``VtopConnectionError``
     - The request never completed. Carries ``original_exception``.
   * - ``VtopParsingError``
     - The page loaded but did not look like we expect. Usually VTOP changed.
   * - Per-feature errors
     - ``VtopAttendanceError``, ``VtopMarksError``, ``VtopGeneralOutingError``
       and so on, for failures inside one feature.

The rejection modal
-------------------

VTOP answers a rejected request with a small fragment reading
*"This menu is not available at present!!!"* — served with **HTTP 200**, so
nothing about the status tells you anything is wrong.

The same body comes back for two causes that the response gives no way to
separate:

* the request shape was wrong
* the portal has genuinely switched that menu off

``VtopMenuUnavailableError`` says exactly that much and no more, because from
the response alone there is nothing more to say.

Empty is not an error
---------------------

Several results are legitimately empty and the library will not raise for them:

* ``get_grade_view`` returns ``[]`` for the current semester until results
  publish
* marks may not be published yet
* biometric can be genuinely empty for a day
* an **unknown semester id** also returns an empty result — VTOP does not
  reject it, so a wrong id looks the same as a quiet semester. Take ids from
  :meth:`~vitap_vtop_client.client.VtopClient.get_semesters`.

Timeouts
--------

httpx raises its transport errors with an empty message, so a naive
``f"failed: {e}"`` produces a message that stops at the colon.
``VtopConnectionError`` names the underlying class instead, which is what
separates a read timeout from a refused connection.
