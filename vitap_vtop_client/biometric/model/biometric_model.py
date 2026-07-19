from pydantic import BaseModel


class BiometricModel(BaseModel):
    serial: str
    date: str
    in_time: str
    location: str
    # VTOP does not currently serve these on the biometric log page. They are
    # kept so the shape matches the lib_vtop rust crate.
    day: str = ""
    out_time: str = ""
    duration: str = ""
