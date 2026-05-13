import sqlite3
from datetime import datetime

class HotelService:
    def __init__(self, db_name="hotel_pms.db"):
        self.conn = sqlite3.connect(db_name)
        self._initialize_db()

    def _initialize_db(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT);
                CREATE TABLE IF NOT EXISTS rooms (room_id TEXT PRIMARY KEY, type TEXT, price REAL, status TEXT DEFAULT 'Trống');
                CREATE TABLE IF NOT EXISTS customers (cmnd TEXT PRIMARY KEY, name TEXT, phone TEXT);
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, room_id TEXT, cmnd TEXT, check_in_time TEXT, check_out_time TEXT, 
                    total_fee REAL DEFAULT 0, status TEXT DEFAULT 'Đang Thuê'
                );
            """)
            
            if self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                self.conn.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", [('admin', '123456', 'Quản lý'), ('letan', '123456', 'Lễ tân')])
            if self.conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
                rooms = [('101', 'Standard', 300000), ('102', 'Standard', 300000), ('201', 'VIP', 800000), ('202', 'VIP', 800000)]
                self.conn.executemany("INSERT INTO rooms (room_id, type, price, status) VALUES (?, ?, ?, 'Trống')", rooms)

    # ================= LOGIC NGƯỜI DÙNG (MỚI) =================
    def get_all_users(self):
        return self.conn.execute("SELECT id, username, password, role FROM users").fetchall()

    def add_user(self, username, password, role):
        if not username or not password or not role: raise Exception("Vui lòng điền đủ thông tin!")
        exist = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if exist: raise Exception("Tên đăng nhập đã tồn tại!")
        with self.conn:
            self.conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))

    def update_user(self, user_id, username, password, role):
        if not username or not password or not role: raise Exception("Vui lòng điền đủ thông tin!")
        with self.conn:
            self.conn.execute("UPDATE users SET username=?, password=?, role=? WHERE id=?", (username, password, role, user_id))

    def delete_user(self, user_id):
        with self.conn:
            self.conn.execute("DELETE FROM users WHERE id=?", (user_id,))

    # ================= CÁC LOGIC CŨ GIỮ NGUYÊN =================
    def login(self, username, password):
        user = self.conn.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        return user[0] if user else None

    def get_dashboard_stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        rented = self.conn.execute("SELECT COUNT(*) FROM rooms WHERE status='Đang Thuê'").fetchone()[0]
        rev = self.conn.execute("SELECT SUM(total_fee) FROM bookings WHERE status='Đã Trả'").fetchone()[0] or 0
        bookings_count = self.conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        return total, rented, total - rented, rev, bookings_count

    def get_recent_bookings(self):
        query = """
            SELECT b.id, c.name, r.type, b.room_id, b.check_in_time, b.status 
            FROM bookings b JOIN customers c ON b.cmnd = c.cmnd JOIN rooms r ON b.room_id = r.room_id
            ORDER BY b.id DESC LIMIT 10
        """
        return self.conn.execute(query).fetchall()

    def get_all_rooms(self): return self.conn.execute("SELECT * FROM rooms").fetchall()
    def get_empty_rooms(self): return self.conn.execute("SELECT room_id, type FROM rooms WHERE status='Trống'").fetchall()

    def add_room(self, room_id, room_type, price):
        exist = self.conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if exist: raise Exception(f"Mã phòng {room_id} đã tồn tại trong hệ thống!")
        with self.conn:
            self.conn.execute("INSERT INTO rooms (room_id, type, price, status) VALUES (?, ?, ?, 'Trống')", (room_id, room_type, price))

    def check_in(self, room_id, name, cmnd, phone=""):
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO customers (cmnd, name, phone) VALUES (?, ?, ?)", (cmnd, name, phone))
            self.conn.execute("UPDATE rooms SET status='Đang Thuê' WHERE room_id=?", (room_id,))
            self.conn.execute("INSERT INTO bookings (room_id, cmnd, check_in_time) VALUES (?, ?, ?)", (room_id, cmnd, time_now))

    def check_out(self, room_id):
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        price = self.conn.execute("SELECT price FROM rooms WHERE room_id=?", (room_id,)).fetchone()[0]
        with self.conn:
            self.conn.execute("UPDATE rooms SET status='Trống' WHERE room_id=?", (room_id,))
            self.conn.execute("UPDATE bookings SET status='Đã Trả', check_out_time=?, total_fee=? WHERE room_id=? AND status='Đang Thuê'", (time_now, price, room_id))