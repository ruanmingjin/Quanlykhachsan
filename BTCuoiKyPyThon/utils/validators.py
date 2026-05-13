from exceptions.hotel_exceptions import InvalidDataError

def validate_cmnd(cmnd: str):
    if not cmnd.isdigit() or len(cmnd) not in [9, 12]:
        raise InvalidDataError("CMND/CCCD phải là số và có 9 hoặc 12 ký tự!")
    return True