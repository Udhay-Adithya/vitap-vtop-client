Getting started
===============

Installation
------------

.. code-block:: bash

   pip install git+https://github.com/Udhay-Adithya/vitap-vtop-client.git

Requires Python 3.13 or newer. The captcha is solved locally by a small bundled
model, so there is no external service to configure and no key to obtain.

Everything is asynchronous. There is no synchronous API.

Your first request
------------------

:class:`~vitap_vtop_client.client.VtopClient` is the only entry point. It is an
async context manager, which closes the underlying HTTP session for you.

.. code-block:: python

   async with VtopClient("REGNO", "password") as client:
       profile = await client.get_profile()
       print(profile.student_name)

Logging in is explicit, and VTOP may interrupt it with an OTP. See
:doc:`guide/authentication` before writing anything beyond a script you run by
hand.

Semester ids
------------

Most methods take a ``sem_sub_id``. Do not hardcode one — ask VTOP:

.. code-block:: python

   semesters = await client.get_semesters()
   for semester in semesters.semesters:
       print(semester.id, semester.name)

The library used to ship a hardcoded map of these and it went stale, which is
worse than it sounds: VTOP does not reject an unknown id. It returns an empty
result, so a wrong semester looks exactly like a semester with no data.

Being a good citizen
--------------------

Every call is a real request against a university server that is not built for
automation, and logging in is captcha gated and may need an OTP a human has to
read from their email.

* Reuse one client for many calls rather than building one per request.
* Never loop on a failed login. Repeated failures can lock a VTOP account.
* Treat an empty result as legitimate. Marks may be unpublished, biometric can
  be genuinely empty for a day, and grades do not exist until a semester ends.
