vitap-vtop-client
=================

An asynchronous Python client for the VIT-AP VTOP student portal.

There is no VTOP API. Every feature here is scraped out of a JSP application
that changes without warning, so this library is as much a record of how the
portal actually behaves as it is a wrapper around it. Where VTOP does something
surprising, the docs say so rather than hiding it.

.. code-block:: python

   import asyncio
   from vitap_vtop_client import VtopClient
   from vitap_vtop_client.exceptions import VtopLoginOtpRequiredError

   async def main():
       async with VtopClient("REGNO", "password") as client:
           try:
               await client.login()
           except VtopLoginOtpRequiredError:
               await client.verify_login_otp(input("OTP: "))

           semesters = await client.get_semesters()
           attendance = await client.get_attendance(semesters.semesters[0].id)
           for course in attendance:
               print(course.course_code, course.attendance_percentage)

   asyncio.run(main())

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting-started

.. toctree::
   :maxdepth: 2
   :caption: Guide

   guide/authentication
   guide/sessions
   guide/errors
   guide/vtop-quirks

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/client
   api/models
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
