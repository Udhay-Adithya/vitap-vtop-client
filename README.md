<br />
<p align="center">
    <img src="public/Final_Icon_512x512.png" width="100" height="100" style="margin-right: 60px;"> 
    <img src="public/vitaplogo.png" width="322" height="100"> 
</p>
<br>
<br>

<p align="center">
    <a href="https://github.com/Udhay-Adithya/vitap-vtop-client">
    <img src="https://img.shields.io/github/stars/Udhay-Adithya/vitap-vtop-client?style=social" alt="License: MIT">
    </a>
    <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
    </a>
    <img src="https://img.shields.io/badge/Version-0.2.8-blue.svg" alt="Version 0.2.8">
    <a href="https://github.com/Udhay-Adithya/vitap-vtop-client/issues">
    <img src="https://img.shields.io/github/issues/Udhay-Adithya/vitap-vtop-client" alt="License: MIT">
    </a>
</p>
<br>

`vitap-vtop-client` is a Python library providing a programmatic interface for interacting with the VIT-AP VTOP student portal. It simplifies web scraping, session management, CAPTCHA handling, and HTML parsing, offering structured access to student information.

This library is designed as a backend component for applications needing VTOP data, such as mobile apps, web services, or analytical tools.

**Disclaimer:** Use this library responsibly and in accordance with VIT-AP's terms of service. Web scraping is subject to changes in the target website's structure, which may occasionally affect the library's functionality.

## Table of Contents
1. [Features](#features)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Documentation](#documentation)
5. [Contributing](#contributing)
6. [License](#license)
7. [Related Project: VTOP API](#related-project-vtop-api)

## Features
*   **User Authentication:** Secure login and session management.
*   **Profile Information:** Retrieve comprehensive student profile details.
*   **Academic Data:** Access attendance records, timetables, marks, and exam schedules.
*   **Biometric Logs:** Fetch student biometric entry/exit logs.
*   **Contact Details:** View mentor, HOD, and Dean information.
*   **Financial Information:** Check pending payments and download receipts.
*   **Hostel Outing Requests:** Post and review weekend and general outing requests.
*   **Academic Performance:** Retrieve NCGPA and rank details.

## Installation

If you want to use `vitap-vtop-client` in your project, you can install it directly from GitHub.

**Using `pip` (recommended for adding to `requirements.txt`):**

```bash
pip install git+https://github.com/Udhay-Adithya/vitap-vtop-client.git@main
```

**Using `poetry`:**

```bash
poetry add git+https://github.com/Udhay-Adithya/vitap-vtop-client.git@main
```

## Quick Start

Here's a basic example of how to log in and fetch attendance data:

```python
import asyncio
from vitap_vtop_client.client import VtopClient
from vitap_vtop_client.exceptions import VitapVtopClientError, VtopLoginError

async def main():
    async with VtopClient("your_registration_number", "your_password") as client:
        try:
            fall_sem_2024_25 = "AP2024252"
            attendance_data = await client.get_attendance(sem_sub_id=fall_sem_2024_25)
            print(attendance_data)

        except VtopLoginError as e:
            print(f"A login-specific error occurred: {e}")
        except VitapVtopClientError as e:
            print(f"A client error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

For comprehensive information on all available methods, data models, and advanced usage, please refer to the main documentation:

➡️ **[udhay-adithya.github.io/vitap-vtop-client](https://udhay-adithya.github.io/vitap-vtop-client/)**

The API reference there is generated from the docstrings, so it cannot drift from the code. It also covers the things VTOP does that are worth knowing before you build on it: the login OTP gate, reusing a session across processes, and what an empty result actually means.

## Contributing
Contributions are welcome! We appreciate any help, from bug reports and fixes to feature suggestions and documentation improvements.

Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute, set up your development environment, and submit pull requests.

## License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## Related Project: VTOP API
For those looking for a ready-to-use API service built on top of this library, check out the **VITAP-VTOP API**:

➡️ **[VITAP-VTOP API Repository](https://github.com/Udhay-Adithya/vit_ap_vtop_api/)**

This FastAPI wrapper allows easy access to VTOP data without needing to integrate the client library directly. We encourage users to try out the API and provide feedback.
