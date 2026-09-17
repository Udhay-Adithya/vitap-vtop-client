VTOP quirks
===========

Behaviour of the portal that the library works around, recorded so nobody has
to rediscover it. Verified against live VTOP on 2026-09-17.

TLS
---

VTOP's server omits the Sectigo intermediate CA from its chain. Browsers and
curl fetch the missing certificate automatically; Python's ``ssl`` does not, so
requests fail with ``CERTIFICATE_VERIFY_FAILED``.

The library bundles that intermediate and verifies against certifi's roots plus
it. Verification stays fully enabled — nothing is bypassed, and a TLS error
should never be "fixed" with ``verify=False``.

Everything returns HTTP 200
---------------------------

A rejected request, a disabled menu and a page full of data all come back as
200. Status codes carry almost no information here, with one exception: a 404
on a POST means the CSRF token or session has expired.

Semester lists differ by page
-----------------------------

The timetable and attendance pages list only the student's own semesters and
are **empty for freshers**. Marks, exam schedule and grade view render the full
institutional list for anyone. ``get_semesters`` prefers the first and falls
back to the others.

The weekend outing form has a window
------------------------------------

It is only served Tuesday 00:00 to Friday 23:59. Outside that window VTOP
returns the page with no student fields at all. The parser raises an error
naming the window rather than reporting a malformed page.

Colour is not status
--------------------

VTOP paints the pending outing status, "Waiting for Mentor's Approval", in red.
Red means pending, not failed. An earlier version read the styling as an error
and reported successful submissions as failures.

Outing writes return the whole page
-----------------------------------

Submitting or deleting an outing request returns the entire page reloaded
rather than a status message — VTOP's success popups are commented out server
side. The caller has to supply the wording that counts as success.

Request shapes are not interchangeable
--------------------------------------

Page shells take ``verifyMenu``, ``authorizedID``, ``_csrf`` and ``nocache``
(epoch milliseconds). Data endpoints take ``_csrf``, ``authorizedID`` and ``x``
(an RFC 1123 UTC timestamp) and reject the other shape outright. Some endpoints
also refuse to answer without ``X-Requested-With: XMLHttpRequest``.

Some endpoints need priming, most do not
----------------------------------------

The course page will not answer its dropdown lookups until ``StudentCoursePage``
has been opened, and a digital assignment upload is rejected unless
``processDigitalAssignment`` was posted for that class first.

Attendance, marks, exam schedule, timetable and grade view need no such priming,
despite once being written as if they did.

VTOP keeps its typos
--------------------

The receipt download really does take a ``receitNo`` query parameter. Do not
"fix" it.
