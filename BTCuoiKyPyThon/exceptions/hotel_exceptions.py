class HotelException(Exception): pass

class RoomUnavailableError(HotelException):
    def __init__(self, room_id):
        super().__init__(f"Phòng {room_id} hiện đang có khách thuê!")

class InvalidDataError(HotelException):
    def __init__(self, message):
        super().__init__(f"Lỗi nhập liệu: {message}")