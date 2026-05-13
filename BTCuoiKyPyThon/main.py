import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import customtkinter as ctk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

try:
    from ttkbootstrap.widgets import ToastNotification
except ImportError:
    from ttkbootstrap.toast import ToastNotification

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import os
import sqlite3

from services.hotel_service import HotelService
from utils.validators import validate_cmnd
from utils.formatters import format_currency

plt.rcParams["font.family"] = "Segoe UI"


class HotelManagementApp(tb.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.service = HotelService()
        self.room_status_overrides = {}
        self.active_stays = {}
        self.transaction_history = []

        try:
            _, _, _, rev, _ = self.service.get_dashboard_stats()
            self.total_revenue = float(rev)
        except Exception:
            self.total_revenue = 3000000.0

        try:
            old_rows = self.service.get_recent_bookings()
        except Exception:
            old_rows = []

        for row in old_rows:
            try:
                self.transaction_history.append({
                    "invoice": row[0],
                    "customer": row[1],
                    "room_type": row[2],
                    "room_id": str(row[3]),
                    "time": row[4],
                    "status": row[5],
                    "amount": 0,
                })
            except Exception:
                pass

        self.invoice_seq = len(self.transaction_history) + 1

        self.financial_seq = 8402
        self.financial_data = [
            {
                "code": "GD_8401",
                "date": "Hôm nay",
                "type": "THU",
                "description": "Doanh thu ban đầu từ hệ thống",
                "amount": float(self.total_revenue),
                "source": "Hệ thống",
            }
        ]

        self.support_data = [
            {
                "request_id": "RQ-101",
                "area": "Tầng 1",
                "service": "Sửa chữa",
                "status": "Đang xử lý",
                "guest": "Phòng 101",
                "priority": "Cao",
                "staff": "Kỹ thuật",
                "note": "Kiểm tra điều hòa và ổ điện phòng 101.",
                "time": "2026-05-12 09:30:00",
            },
            {
                "request_id": "RQ-102",
                "area": "Tầng 2",
                "service": "Thêm khăn",
                "status": "Chờ xử lý",
                "guest": "Phòng 203",
                "priority": "Trung bình",
                "staff": "Housekeeping",
                "note": "Khách yêu cầu thêm 2 khăn tắm.",
                "time": "2026-05-12 10:15:00",
            },
            {
                "request_id": "RQ-103",
                "area": "Sảnh",
                "service": "Hỗ trợ hành lý",
                "status": "Hoàn thành",
                "guest": "Khách lẻ",
                "priority": "Thấp",
                "staff": "Bellman",
                "note": "Hỗ trợ khách mang hành lý ra xe.",
                "time": "2026-05-12 08:20:00",
            },
        ]

        self.colors = {
            "bg": "#f5f7fb",
            "card": "#ffffff",
            "navy": "#071a2f",
            "navy_2": "#10243d",
            "orange": "#f97316",
            "orange_2": "#fb923c",
            "text": "#0f172a",
            "muted": "#64748b",
            "border": "#e2e8f0",
            "green": "#10b981",
            "red": "#ef4444",
            "blue": "#3b82f6",
            "teal": "#14b8a6",
            "purple": "#8b5cf6",
            "soft_blue": "#eaf3ff",
            "soft_green": "#e8fff7",
            "soft_orange": "#fff3df",
            "soft_purple": "#f1eaff",
            "soft_red": "#fef2f2",
        }

        self._init_local_database()
        self._load_persistent_state()

        self._setup_global_typography()
        self._setup_global_button_theme()

        self.title("MingJin PMS - Hệ thống quản lý khách sạn")
        self.geometry("1180x760")
        self.minsize(1050, 700)
        self.position_center()
        self.show_login_screen()

    # =====================================================
    #  COMMON UI HELPERS
    # =====================================================
    def show_toast(self, title, message, bootstyle="success", duration=2500):
        try:
            ToastNotification(title=title, message=message, duration=duration, bootstyle=bootstyle).show_toast()
        except TypeError:
            ToastNotification(title, message, duration, bootstyle).show_toast()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def make_card(self, parent, padx=18, pady=18, bg="#ffffff"):
        return tk.Frame(
            parent,
            bg=bg,
            padx=padx,
            pady=pady,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )

    def create_stat_card(self, parent, col, title, value, color=None, bg=None):
        color = color or self.colors["blue"]
        bg = bg or self.colors["soft_blue"]
        parent.columnconfigure(col, weight=1)
        card = tk.Frame(parent, bg="#ffffff", padx=16, pady=12, highlightbackground=self.colors["border"], highlightthickness=1)
        card.grid(row=0, column=col, sticky=EW, padx=6)
        tk.Label(card, text=title, bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 9, "bold")).pack(anchor=W)
        lbl = tk.Label(card, text=value, bg="#ffffff", fg=color, font=("Segoe UI", 20, "bold"))
        lbl.pack(anchor=W, pady=(4, 0))
        return lbl

    def _fill_text(self, widget, content):
        widget.config(state="normal")
        widget.delete("1.0", END)
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def _now_str(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _next_invoice_id(self):
        current = self.invoice_seq
        self.invoice_seq += 1
        return current

    def get_room_info_by_id(self, room_id):
        room_id = str(room_id)
        for room in self.get_display_rooms():
            if str(room[0]) == room_id:
                return room
        return None

    def get_live_dashboard_stats(self):
        rooms = self.get_display_rooms()
        rented = sum(1 for r in rooms if self.normalize_room_status(r[3]) == "Đang sử dụng")
        empty = sum(1 for r in rooms if self.normalize_room_status(r[3]) == "Trống")
        total = len(rooms)
        bookings = len(self.transaction_history)
        revenue = self.total_revenue
        return total, rented, empty, revenue, bookings

    def _next_financial_code(self):
        code = f"GD_{self.financial_seq}"
        self.financial_seq += 1
        return code

    def add_financial_transaction(self, trans_type, amount, description, source="Hệ thống", affects_revenue=False):
        amount = float(amount)
        trans_type = str(trans_type).upper().strip()
        record = {
            "code": self._next_financial_code(),
            "date": self._now_str(),
            "type": trans_type,
            "description": description,
            "amount": amount,
            "source": source,
        }
        self.financial_data.insert(0, record)
        if affects_revenue and trans_type == "THU":
            self.total_revenue += amount
        self._save_financial(record)
        if hasattr(self, "tree_financial"):
            self.refresh_financials()
        return record

    def get_financial_totals(self):
        total_income = sum(float(x["amount"]) for x in self.financial_data if x["type"] == "THU")
        total_expense = sum(float(x["amount"]) for x in self.financial_data if x["type"] == "CHI")
        profit = total_income - total_expense
        return total_income, total_expense, profit

    # =====================================================
    #  LOCAL DATABASE PERSISTENCE
    # =====================================================
    def _db_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "mingjin_pms_state.db")

    def _connect_state_db(self):
        return sqlite3.connect(self._db_path())

    def _init_local_database(self):
        conn = self._connect_state_db()
        cur = conn.cursor()

        # 1) Tài khoản người dùng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2) Danh mục phòng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rooms_master (
                room_id TEXT PRIMARY KEY,
                room_type TEXT,
                price REAL DEFAULT 0,
                floor INTEGER,
                note TEXT
            )
        """)

        # 3) Trạng thái phòng hiện tại
        cur.execute("""
            CREATE TABLE IF NOT EXISTS room_state (
                room_id TEXT PRIMARY KEY,
                status TEXT NOT NULL
            )
        """)

        # 4) Hồ sơ khách hàng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                id_card TEXT,
                phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5) Phiếu đặt / nhận phòng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                room_id TEXT,
                checkin_time TEXT,
                checkout_time TEXT,
                status TEXT,
                amount REAL DEFAULT 0,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
            )
        """)

        # 6) Lịch sử giao dịch khách hàng trên dashboard
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                invoice INTEGER PRIMARY KEY,
                customer TEXT,
                room_type TEXT,
                room_id TEXT,
                time TEXT,
                status TEXT,
                amount REAL DEFAULT 0
            )
        """)

        # 7) Sổ tài chính thu / chi
        cur.execute("""
            CREATE TABLE IF NOT EXISTS financials (
                code TEXT PRIMARY KEY,
                date TEXT,
                type TEXT,
                description TEXT,
                amount REAL DEFAULT 0,
                source TEXT
            )
        """)

        # 8) Tin nhắn nội bộ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS internal_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                title TEXT,
                time TEXT,
                status TEXT,
                priority TEXT,
                content TEXT
            )
        """)

        # 9) Công việc dọn dẹp
        cur.execute("""
            CREATE TABLE IF NOT EXISTS housekeeping_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT,
                task TEXT,
                staff TEXT,
                shift TEXT,
                priority TEXT,
                status TEXT,
                note TEXT
            )
        """)

        # 10) Kho vật tư
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                code TEXT PRIMARY KEY,
                name TEXT,
                stock INTEGER DEFAULT 0,
                unit TEXT,
                category TEXT,
                status TEXT,
                supplier TEXT,
                note TEXT
            )
        """)

        # 11) Lịch trình / sự kiện
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                type TEXT,
                location TEXT,
                person TEXT,
                status TEXT,
                note TEXT
            )
        """)

        # 12) Yêu cầu hỗ trợ khách hàng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_requests (
                request_id TEXT PRIMARY KEY,
                area TEXT,
                service TEXT,
                status TEXT,
                guest TEXT,
                priority TEXT,
                staff TEXT,
                note TEXT,
                time TEXT
            )
        """)

        # 13) Đánh giá khách hàng
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                target TEXT,
                rating TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 14) Nhật ký hệ thống
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        self._sync_service_users_to_state_db()
        self._seed_default_database_rows()

    def _sync_service_users_to_state_db(self):
        """Đồng bộ bảng người dùng từ HotelService sang CSDL trạng thái để CSDL có đủ bảng tài khoản."""
        try:
            users = self.service.get_all_users()
        except Exception:
            users = []
        if not users:
            return
        conn = self._connect_state_db()
        cur = conn.cursor()
        for user in users:
            try:
                cur.execute(
                    "INSERT OR REPLACE INTO app_users(id, username, password, role) VALUES (?, ?, ?, ?)",
                    (int(user[0]), user[1], user[2], user[3]),
                )
            except Exception:
                pass
        conn.commit()
        conn.close()

    def _seed_default_database_rows(self):
        """Thêm dữ liệu mẫu vào các bảng nghiệp vụ nếu bảng đang trống."""
        conn = self._connect_state_db()
        cur = conn.cursor()

        def table_empty(table_name):
            try:
                return cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] == 0
            except Exception:
                return False

        if table_empty("rooms_master"):
            demo_types = ["Standard", "Superior", "Deluxe", "VIP", "Suite", "Family"]
            demo_prices = {"Standard": 300000, "Superior": 450000, "Deluxe": 600000, "VIP": 800000, "Suite": 1200000, "Family": 950000}
            for floor in range(1, 7):
                for index in range(1, 9):
                    room_id = f"{floor}{index:02d}"
                    room_type = demo_types[(floor + index) % len(demo_types)]
                    cur.execute(
                        "INSERT OR IGNORE INTO rooms_master(room_id, room_type, price, floor, note) VALUES (?, ?, ?, ?, ?)",
                        (room_id, room_type, demo_prices[room_type], floor, "Phòng mẫu theo sơ đồ khách sạn"),
                    )

        if table_empty("internal_messages"):
            rows = [
                ("Lễ tân - Hà", "Yêu cầu kiểm tra phòng 203", "10:30 AM", "Chưa đọc", "Cao", "Khách phản ánh điều hòa phòng 203 hoạt động không ổn định. Nhờ bộ phận kỹ thuật kiểm tra sớm."),
                ("Housekeeping", "Hoàn tất dọn phòng 105", "09:45 AM", "Đã đọc", "Thường", "Phòng 105 đã được dọn dẹp xong và sẵn sàng tiếp nhận khách mới."),
                ("Kho vật tư", "Cần bổ sung khăn tắm", "08:20 AM", "Chưa đọc", "Trung bình", "Số lượng khăn tắm tại tầng 4 đang giảm. Đề nghị cấp bổ sung trong ca sáng."),
            ]
            cur.executemany("INSERT INTO internal_messages(sender, title, time, status, priority, content) VALUES (?, ?, ?, ?, ?, ?)", rows)

        if table_empty("housekeeping_tasks"):
            rows = [
                ("Phòng 101", "Dọn phòng sau checkout", "Nguyễn Thị Mai", "Ca sáng", "Cao", "Chờ xử lý", "Khách vừa trả phòng, cần thay ga giường."),
                ("Phòng 203", "Bổ sung amenities", "Trần Thị Lan", "Ca chiều", "Trung bình", "Đang thực hiện", "Bổ sung khăn tắm, nước suối, bàn chải."),
                ("Khu A", "Dọn hành lang", "Nguyễn Thị Mai", "Ca sáng", "Thường", "Hoàn thành", "Đã vệ sinh hành lang và khu vực thang máy."),
            ]
            cur.executemany("INSERT INTO housekeeping_tasks(area, task, staff, shift, priority, status, note) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

        if table_empty("inventory_items"):
            rows = [
                ("VT001", "Giấy in A4", 150, "Ream", "Văn phòng phẩm", "An toàn", "Thiên Long", "Dùng cho lễ tân và kế toán."),
                ("VT002", "Khăn tắm", 18, "Cái", "Buồng phòng", "Sắp hết", "Hotel Supply", "Cần nhập thêm trong tuần này."),
                ("VT003", "Nước suối", 320, "Chai", "Minibar", "An toàn", "Lavie", "Phục vụ khách lưu trú."),
            ]
            cur.executemany("INSERT OR IGNORE INTO inventory_items(code, name, stock, unit, category, status, supplier, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

        if table_empty("calendar_events"):
            rows = [
                ("26/05/2025", "08:30", "Họp nội bộ", "Phòng họp A", "Ban quản lý", "Sắp diễn ra", "Họp giao ban đầu tuần."),
                ("26/05/2025", "14:00", "Kiểm tra thiết bị", "Tầng 3", "Kỹ thuật", "Đang thực hiện", "Kiểm tra điều hòa và thiết bị điện."),
                ("27/05/2025", "09:00", "Đón đoàn khách", "Sảnh chính", "Lễ tân", "Sắp diễn ra", "Chuẩn bị tiếp đón đoàn 12 khách."),
            ]
            cur.executemany("INSERT INTO calendar_events(date, time, type, location, person, status, note) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

        if table_empty("support_requests"):
            rows = [
                ("RQ-101", "Tầng 1", "Sửa chữa", "Đang xử lý", "Phòng 101", "Cao", "Kỹ thuật", "Kiểm tra điều hòa và ổ điện phòng 101.", "2026-05-12 09:30:00"),
                ("RQ-102", "Tầng 2", "Thêm khăn", "Chờ xử lý", "Phòng 203", "Trung bình", "Housekeeping", "Khách yêu cầu thêm 2 khăn tắm.", "2026-05-12 10:15:00"),
                ("RQ-103", "Sảnh", "Hỗ trợ hành lý", "Hoàn thành", "Khách lẻ", "Thấp", "Bellman", "Hỗ trợ khách mang hành lý ra xe.", "2026-05-12 08:20:00"),
            ]
            cur.executemany("INSERT OR IGNORE INTO support_requests(request_id, area, service, status, guest, priority, staff, note, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        if table_empty("customer_reviews"):
            cur.execute(
                "INSERT INTO customer_reviews(customer_name, target, rating, content) VALUES (?, ?, ?, ?)",
                ("Anh Khang", "Dịch vụ", "⭐⭐⭐⭐⭐", "Rất tốt!"),
            )

        conn.commit()
        conn.close()

    def _save_audit_log(self, action, detail):
        try:
            conn = self._connect_state_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO audit_logs(action, detail) VALUES (?, ?)", (action, detail))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _load_persistent_state(self):
        conn = self._connect_state_db()
        cur = conn.cursor()

        try:
            rows = cur.execute("SELECT room_id, status FROM room_state").fetchall()
            self.room_status_overrides = {str(room_id): status for room_id, status in rows}
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT invoice, customer, room_type, room_id, time, status, amount FROM transactions ORDER BY invoice DESC"
            ).fetchall()
            if rows:
                self.transaction_history = [
                    {
                        "invoice": row[0],
                        "customer": row[1],
                        "room_type": row[2],
                        "room_id": str(row[3]),
                        "time": row[4],
                        "status": row[5],
                        "amount": float(row[6] or 0),
                    }
                    for row in rows
                ]
                self.invoice_seq = max(int(row[0]) for row in rows) + 1
                self.active_stays = {
                    str(item["room_id"]): item
                    for item in self.transaction_history
                    if item["status"] in ["Đang ở", "Đang sử dụng"]
                }
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT code, date, type, description, amount, source FROM financials ORDER BY code DESC"
            ).fetchall()
            if rows:
                self.financial_data = [
                    {
                        "code": row[0],
                        "date": row[1],
                        "type": row[2],
                        "description": row[3],
                        "amount": float(row[4] or 0),
                        "source": row[5],
                    }
                    for row in rows
                ]
                numbers = []
                for item in self.financial_data:
                    try:
                        numbers.append(int(str(item["code"]).replace("GD_", "")))
                    except Exception:
                        pass
                self.financial_seq = (max(numbers) + 1) if numbers else self.financial_seq
                self.total_revenue = sum(float(x["amount"]) for x in self.financial_data if x["type"] == "THU")
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT request_id, area, service, status, guest, priority, staff, note, time FROM support_requests ORDER BY request_id DESC"
            ).fetchall()
            if rows:
                self.support_data = [
                    {
                        "request_id": row[0],
                        "area": row[1],
                        "service": row[2],
                        "status": row[3],
                        "guest": row[4],
                        "priority": row[5],
                        "staff": row[6],
                        "note": row[7],
                        "time": row[8],
                    }
                    for row in rows
                ]
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT sender, title, time, status, priority, content FROM internal_messages ORDER BY id DESC"
            ).fetchall()
            if rows:
                self.message_data = [
                    {"sender": r[0], "title": r[1], "time": r[2], "status": r[3], "priority": r[4], "content": r[5]}
                    for r in rows
                ]
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT area, task, staff, shift, priority, status, note FROM housekeeping_tasks ORDER BY id DESC"
            ).fetchall()
            if rows:
                self.housekeeping_data = [
                    {"area": r[0], "task": r[1], "staff": r[2], "shift": r[3], "priority": r[4], "status": r[5], "note": r[6]}
                    for r in rows
                ]
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT code, name, stock, unit, category, status, supplier, note FROM inventory_items ORDER BY code ASC"
            ).fetchall()
            if rows:
                self.inventory_data = [
                    {"code": r[0], "name": r[1], "stock": int(r[2] or 0), "unit": r[3], "category": r[4], "status": r[5], "supplier": r[6], "note": r[7]}
                    for r in rows
                ]
        except Exception:
            pass

        try:
            rows = cur.execute(
                "SELECT date, time, type, location, person, status, note FROM calendar_events ORDER BY id DESC"
            ).fetchall()
            if rows:
                self.calendar_data = [
                    {"date": r[0], "time": r[1], "type": r[2], "location": r[3], "person": r[4], "status": r[5], "note": r[6]}
                    for r in rows
                ]
        except Exception:
            pass

        conn.close()

    def _save_room_master(self, room_id, room_type, price, note=""):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO rooms_master(room_id, room_type, price, floor, note) VALUES (?, ?, ?, ?, ?)",
            (str(room_id), room_type, float(price), self.get_room_floor(room_id), note),
        )
        conn.commit()
        conn.close()

    def _save_customer_and_booking(self, customer_name, id_card, phone, room_id, amount, status="Đang ở"):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO customers(full_name, id_card, phone) VALUES (?, ?, ?)",
            (customer_name, id_card, phone),
        )
        customer_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO bookings(customer_id, room_id, checkin_time, checkout_time, status, amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (customer_id, str(room_id), self._now_str(), "", status, float(amount)),
        )
        conn.commit()
        conn.close()
        return customer_id

    def _close_booking_for_room(self, room_id, amount):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE bookings
            SET checkout_time = ?, status = ?, amount = ?
            WHERE room_id = ? AND status IN ('Đang ở', 'Đang sử dụng')
            """,
            (self._now_str(), "Đã Trả", float(amount), str(room_id)),
        )
        conn.commit()
        conn.close()

    def _save_room_state(self, room_id, status):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO room_state(room_id, status) VALUES (?, ?)",
            (str(room_id), status),
        )
        conn.commit()
        conn.close()

    def _save_transaction(self, item):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO transactions(invoice, customer, room_type, room_id, time, status, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(item["invoice"]),
                item.get("customer", ""),
                item.get("room_type", ""),
                str(item.get("room_id", "")),
                item.get("time", ""),
                item.get("status", ""),
                float(item.get("amount", 0) or 0),
            ),
        )
        conn.commit()
        conn.close()

    def _save_all_transactions(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions")
        for item in self.transaction_history:
            cur.execute(
                """
                INSERT OR REPLACE INTO transactions(invoice, customer, room_type, room_id, time, status, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(item["invoice"]),
                    item.get("customer", ""),
                    item.get("room_type", ""),
                    str(item.get("room_id", "")),
                    item.get("time", ""),
                    item.get("status", ""),
                    float(item.get("amount", 0) or 0),
                ),
            )
        conn.commit()
        conn.close()

    def _save_financial(self, item):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO financials(code, date, type, description, amount, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("code", ""),
                item.get("date", ""),
                item.get("type", ""),
                item.get("description", ""),
                float(item.get("amount", 0) or 0),
                item.get("source", ""),
            ),
        )
        conn.commit()
        conn.close()

    def _save_all_financials(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM financials")
        for item in self.financial_data:
            cur.execute(
                """
                INSERT OR REPLACE INTO financials(code, date, type, description, amount, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("code", ""),
                    item.get("date", ""),
                    item.get("type", ""),
                    item.get("description", ""),
                    float(item.get("amount", 0) or 0),
                    item.get("source", ""),
                ),
            )
        conn.commit()
        conn.close()

    def _save_all_supports(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM support_requests")
        for item in self.support_data:
            cur.execute(
                """
                INSERT OR REPLACE INTO support_requests(request_id, area, service, status, guest, priority, staff, note, time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("request_id", ""),
                    item.get("area", ""),
                    item.get("service", ""),
                    item.get("status", ""),
                    item.get("guest", ""),
                    item.get("priority", ""),
                    item.get("staff", ""),
                    item.get("note", ""),
                    item.get("time", ""),
                ),
            )
        conn.commit()
        conn.close()

    def _save_all_messages(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM internal_messages")
        for item in getattr(self, "message_data", []):
            cur.execute(
                """
                INSERT INTO internal_messages(sender, title, time, status, priority, content)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item.get("sender", ""), item.get("title", ""), item.get("time", ""), item.get("status", ""), item.get("priority", ""), item.get("content", "")),
            )
        conn.commit()
        conn.close()

    def _save_all_housekeeping(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM housekeeping_tasks")
        for item in getattr(self, "housekeeping_data", []):
            cur.execute(
                """
                INSERT INTO housekeeping_tasks(area, task, staff, shift, priority, status, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item.get("area", ""), item.get("task", ""), item.get("staff", ""), item.get("shift", ""), item.get("priority", ""), item.get("status", ""), item.get("note", "")),
            )
        conn.commit()
        conn.close()

    def _save_all_inventory(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_items")
        for item in getattr(self, "inventory_data", []):
            cur.execute(
                """
                INSERT OR REPLACE INTO inventory_items(code, name, stock, unit, category, status, supplier, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item.get("code", ""), item.get("name", ""), int(item.get("stock", 0) or 0), item.get("unit", ""), item.get("category", ""), item.get("status", ""), item.get("supplier", ""), item.get("note", "")),
            )
        conn.commit()
        conn.close()

    def _save_all_calendar(self):
        conn = self._connect_state_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM calendar_events")
        for item in getattr(self, "calendar_data", []):
            cur.execute(
                """
                INSERT INTO calendar_events(date, time, type, location, person, status, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item.get("date", ""), item.get("time", ""), item.get("type", ""), item.get("location", ""), item.get("person", ""), item.get("status", ""), item.get("note", "")),
            )
        conn.commit()
        conn.close()

    def _save_module_by_tree(self, tree):
        if hasattr(self, "tree_messages") and tree is self.tree_messages:
            self._save_all_messages()
            return
        if hasattr(self, "tree_housekeeping") and tree is self.tree_housekeeping:
            self._save_all_housekeeping()
            return
        if hasattr(self, "tree_inventory") and tree is self.tree_inventory:
            self._save_all_inventory()
            return
        if hasattr(self, "tree_calendar") and tree is self.tree_calendar:
            self._save_all_calendar()
            return

    def _setup_global_typography(self):
        try:
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")
        except Exception:
            pass

        try:
            families = set(tkfont.families())
            self.font_family = "Roboto" if "Roboto" in families else "Segoe UI"
        except Exception:
            self.font_family = "Segoe UI"

        self.option_add("*Font", f"{{{self.font_family}}} 10")

        for font_name, size, weight in [
            ("TkDefaultFont", 10, "normal"),
            ("TkTextFont", 10, "normal"),
            ("TkMenuFont", 10, "normal"),
            ("TkHeadingFont", 11, "bold"),
            ("TkCaptionFont", 10, "normal"),
            ("TkSmallCaptionFont", 9, "normal"),
            ("TkIconFont", 10, "normal"),
            ("TkTooltipFont", 9, "normal"),
        ]:
            try:
                named_font = tkfont.nametofont(font_name)
                named_font.configure(family=self.font_family, size=size, weight=weight)
            except Exception:
                pass

        try:
            style = tb.Style()
            style.configure(".", font=(self.font_family, 10))
            style.configure("TLabel", font=(self.font_family, 10))
            style.configure("TEntry", font=(self.font_family, 10))
            style.configure("TCombobox", font=(self.font_family, 10))
            style.configure("Treeview", font=(self.font_family, 10), rowheight=34)
            style.configure("Treeview.Heading", font=(self.font_family, 10, "bold"))
        except Exception:
            pass

    def _setup_global_button_theme(self):
        """
        Không ghi đè tb.Button bằng customtkinter nữa.
        Lý do: ttkbootstrap.Messagebox và một số popup dùng nội bộ tb.Button;
        nếu monkey-patch tb.Button sang CTkButton thì các nút Yes/No/OK có thể bị lỗi không nhận click.
        Giữ tb.Button gốc để toàn bộ chức năng bấm hoạt động ổn định.
        """
        self.round_btn_colors = {
            "primary": ("#1d4ed8", "#1e40af", "#ffffff"),
            "info": ("#3b82f6", "#2563eb", "#ffffff"),
            "success": ("#10b981", "#059669", "#ffffff"),
            "warning": ("#f59e0b", "#d97706", "#ffffff"),
            "danger": ("#ef4444", "#dc2626", "#ffffff"),
            "secondary": ("#334155", "#1e293b", "#ffffff"),
            "dark": ("#0f172a", "#020617", "#ffffff"),
            "light": ("#e2e8f0", "#cbd5e1", "#0f172a"),
        }

    def ui_button(
        self,
        parent,
        text,
        command=None,
        kind="primary",
        width=110,
        height=38,
        text_color="white"
    ):
        """
        Nút bo tròn dùng riêng khi cần trang trí.
        Không dùng để thay thế toàn bộ tb.Button, tránh làm hỏng Messagebox.
        """
        fg, hover, default_text_color = self.round_btn_colors.get(kind, self.round_btn_colors["primary"])
        if text_color == "white":
            text_color = default_text_color
        try:
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                width=width,
                height=height,
                corner_radius=18,
                fg_color=fg,
                hover_color=hover,
                text_color=text_color,
                border_width=0,
                font=(self.font_family, 11, "bold"),
                cursor="hand2",
            )
        except Exception:
            return tb.Button(parent, text=text, command=command)

    def _normalize_font_to_roboto(self, widget):
        try:
            current_font = widget.cget("font")
            if not current_font:
                return
            font_obj = tkfont.Font(font=current_font)
            widget.configure(
                font=(
                    self.font_family,
                    font_obj.actual("size"),
                    font_obj.actual("weight"),
                )
            )
        except Exception:
            pass

    def apply_roboto_to_widget_tree(self, widget):
        self._normalize_font_to_roboto(widget)
        for child in widget.winfo_children():
            self.apply_roboto_to_widget_tree(child)

    def create_module_shell(self, parent, stats_config, left_title, right_title, right_subtitle):
        stats = tk.Frame(parent, bg=self.colors["bg"])
        stats.pack(fill=X, pady=(0, 14))
        stat_labels = []
        for i, (title, color, soft) in enumerate(stats_config):
            stat_labels.append(self.create_stat_card(stats, i, title, "0", color, soft))

        content = tk.Frame(parent, bg=self.colors["bg"])
        content.pack(fill=BOTH, expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        left = self.make_card(content, padx=18, pady=16)
        left.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))
        right = self.make_card(content, padx=22, pady=18)
        right.grid(row=0, column=1, sticky=NSEW, padx=(10, 0))

        left_top = tk.Frame(left, bg="#ffffff")
        left_top.pack(fill=X, pady=(0, 12))
        tk.Label(left_top, text=left_title, bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(side=LEFT)

        tk.Label(right, text=right_title, bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor=W)
        tk.Label(right, text=right_subtitle, bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor=W, pady=(4, 16))
        return stat_labels, left, left_top, right

    # =====================================================
    #  LOGIN SCREEN
    # =====================================================
    def show_login_screen(self):
        self.clear_window()
        self.geometry("1180x760")
        self.minsize(1050, 700)
        self.configure(bg="#f5f7fb")

        root = tk.Frame(self, bg="#f5f7fb")
        root.pack(fill=BOTH, expand=True)

        # ================= LEFT LOGIN AREA =================
        left = tk.Frame(root, bg="#f5f7fb", width=500, padx=28, pady=32)
        left.pack(side=LEFT, fill=Y)
        left.pack_propagate(False)

        card = tk.Frame(
            left,
            bg="#ffffff",
            padx=42,
            pady=34,
            highlightbackground="#e2e8f0",
            highlightthickness=1
        )
        card.pack(fill=BOTH, expand=True)

        # Logo
        logo = tk.Canvas(card, width=72, height=72, bg="#ffffff", highlightthickness=0)
        logo.pack(pady=(0, 10))
        logo.create_oval(6, 6, 66, 66, fill="#fff7ed", outline="#fed7aa", width=2)
        logo.create_polygon(36, 13, 54, 24, 36, 36, 18, 24, fill="#ffffff", outline=self.colors["navy"], width=3)
        logo.create_polygon(18, 24, 36, 36, 36, 57, 18, 45, fill="#ffffff", outline=self.colors["navy"], width=3)
        logo.create_polygon(54, 24, 36, 36, 36, 57, 54, 45, fill="#ffffff", outline=self.colors["navy"], width=3)
        logo.create_line(36, 13, 36, 36, fill=self.colors["orange"], width=3)

        title = tk.Frame(card, bg="#ffffff")
        title.pack()

        tk.Label(title, text="MingJin", bg="#ffffff", fg=self.colors["navy"], font=(self.font_family, 29, "bold")).pack(side=LEFT)
        tk.Label(title, text=" PMS", bg="#ffffff", fg=self.colors["orange"], font=(self.font_family, 29, "bold")).pack(side=LEFT)

        tk.Label(
            card,
            text="Hệ thống quản lý khách sạn",
            bg="#ffffff",
            fg=self.colors["muted"],
            font=(self.font_family, 12)
        ).pack(pady=(6, 28))

        form = tk.Frame(card, bg="#ffffff")
        form.pack(fill=X)

        self.user_var = tb.StringVar(value="admin")
        self.pass_var = tb.StringVar(value="123456")

        tk.Label(form, text="Tài khoản", bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 11, "bold")).pack(anchor=W)
        user_box = tk.Frame(form, bg="#ffffff", highlightbackground="#dbe3ef", highlightthickness=1)
        user_box.pack(fill=X, pady=(8, 18), ipady=2)
        tk.Label(user_box, text="👤", bg="#ffffff", fg=self.colors["muted"], font=(self.font_family, 13)).pack(side=LEFT, padx=(12, 6))
        tk.Entry(user_box, textvariable=self.user_var, relief=FLAT, bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 13)).pack(side=LEFT, fill=X, expand=True, padx=(6, 12), pady=12)

        tk.Label(form, text="Mật khẩu", bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 11, "bold")).pack(anchor=W)
        pass_box = tk.Frame(form, bg="#ffffff", highlightbackground="#dbe3ef", highlightthickness=1)
        pass_box.pack(fill=X, pady=(8, 16), ipady=2)
        tk.Label(pass_box, text="🔒", bg="#ffffff", fg=self.colors["muted"], font=(self.font_family, 13)).pack(side=LEFT, padx=(12, 6))
        tk.Entry(pass_box, textvariable=self.pass_var, show="*", relief=FLAT, bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 13)).pack(side=LEFT, fill=X, expand=True, padx=(6, 12), pady=12)

        opt = tk.Frame(form, bg="#ffffff")
        opt.pack(fill=X, pady=(2, 22))
        tk.Checkbutton(opt, text="Ghi nhớ đăng nhập", bg="#ffffff", activebackground="#ffffff", fg=self.colors["text"], font=(self.font_family, 10), bd=0, highlightthickness=0).pack(side=LEFT)
        tk.Label(opt, text="Quên mật khẩu?", bg="#ffffff", fg="#2563eb", font=(self.font_family, 10, "underline"), cursor="hand2").pack(side=RIGHT)

        tk.Button(
            form,
            text="Đăng nhập  →",
            bg="#334a62",
            fg="#ffffff",
            activebackground="#25384c",
            activeforeground="#ffffff",
            relief=FLAT,
            bd=0,
            cursor="hand2",
            font=(self.font_family, 16, "bold"),
            command=self.handle_login
        ).pack(fill=X, ipady=15, pady=(0, 8))

        # ================= RIGHT HERO AREA =================
        right = tk.Frame(root, bg="#f5f7fb", padx=28, pady=34)
        right.pack(side=LEFT, fill=BOTH, expand=True)

        hero_title = tk.Label(
            right,
            text="Quản lý khách sạn thông minh",
            bg="#f5f7fb",
            fg=self.colors["navy"],
            font=(self.font_family, 26, "bold"),
            anchor=W,
            justify=LEFT,
            wraplength=540
        )
        hero_title.pack(anchor=W, fill=X, pady=(42, 10))

        hero = tk.Canvas(right, bg="#f5f7fb", highlightthickness=0)
        hero.pack(fill=BOTH, expand=True, pady=(18, 0))
        self._draw_login_hero(hero)

    def _draw_login_hero(self, canvas):
        def redraw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 100 or h < 100:
                return

            # Decorative background - chỉ là phần ảnh minh họa, không ảnh hưởng chức năng
            canvas.create_oval(-140, h * 0.60, 220, h * 1.10, fill="#e8eef8", outline="")
            canvas.create_oval(w * 0.73, -90, w * 1.12, h * 0.28, fill="#eef4fb", outline="")
            canvas.create_oval(w * 0.10, h * 0.82, w * 0.96, h * 0.96, fill="#dbe7f5", outline="")

            # Luxury hotel illustration
            x1 = w * 0.20
            y1 = h * 0.27
            x2 = w * 0.82
            y2 = h * 0.82

            # Side buildings
            canvas.create_rectangle(x1 - 72, y1 + 105, x1 + 36, y2 - 20, fill="#173d6b", outline="#245287", width=2)
            canvas.create_rectangle(x2 - 36, y1 + 105, x2 + 72, y2 - 20, fill="#173d6b", outline="#245287", width=2)

            # Main building
            canvas.create_rectangle(x1, y1, x2, y2, fill="#12345b", outline="#245287", width=3)
            canvas.create_rectangle(x1 + 42, y1 - 34, x2 - 42, y1, fill="#1d4778", outline="#245287", width=2)
            canvas.create_rectangle(x1 + 88, y1 - 68, x2 - 88, y1 - 34, fill="#28598e", outline="#245287", width=2)

            # Center tower and golden roof
            tower_x1 = x1 + (x2 - x1) * 0.39
            tower_x2 = x1 + (x2 - x1) * 0.61
            canvas.create_rectangle(tower_x1, y1 - 112, tower_x2, y1, fill="#0f2c4e", outline="#245287", width=2)
            canvas.create_polygon(
                tower_x1 - 12, y1 - 112,
                tower_x2 + 12, y1 - 112,
                (tower_x1 + tower_x2) / 2, y1 - 154,
                fill="#f59e0b",
                outline="#fbbf24",
                width=2
            )

            # Hotel brand name centered above the hotel
            brand_y = y1 - 176
            canvas.create_text(
                (x1 + x2) / 2,
                brand_y,
                text="LUXURY HOTEL",
                fill="#14365d",
                font=(self.font_family, 24, "bold")
            )

            # Five-star sign above hotel name
            star_y = y1 - 206
            start_x = (x1 + x2) / 2 - 52
            for i in range(5):
                canvas.create_text(
                    start_x + i * 26,
                    star_y,
                    text="★",
                    fill="#f59e0b",
                    font=(self.font_family, 15, "bold")
                )

            # Windows
            cols = 6
            rows = 5
            gap_x = (x2 - x1 - 120) / (cols - 1)
            gap_y = (y2 - y1 - 124) / (rows - 1)
            for r in range(rows):
                for c in range(cols):
                    wx = x1 + 46 + c * gap_x
                    wy = y1 + 38 + r * gap_y
                    color = "#f7b02a" if (r + c) % 3 == 0 else "#315f96"
                    canvas.create_rectangle(wx, wy, wx + 29, wy + 42, fill=color, outline="")

            # Entrance
            door_w = 92
            door_h = 116
            dx1 = (x1 + x2) / 2 - door_w / 2
            dy1 = y2 - door_h
            dx2 = dx1 + door_w
            dy2 = y2
            canvas.create_arc(dx1, dy1 - 34, dx2, dy1 + 34, start=0, extent=180, fill="#0f2c4e", outline="#245287", width=2)
            canvas.create_rectangle(dx1, dy1, dx2, dy2, fill="#071c33", outline="#071c33")
            canvas.create_line((dx1 + dx2) / 2, dy1 + 6, (dx1 + dx2) / 2, dy2, fill="#173d6b", width=2)

            # Front steps
            canvas.create_rectangle(dx1 - 46, y2, dx2 + 46, y2 + 12, fill="#d1dae8", outline="")
            canvas.create_rectangle(dx1 - 32, y2 + 12, dx2 + 32, y2 + 23, fill="#c7d3e4", outline="")
            canvas.create_rectangle(dx1 - 18, y2 + 23, dx2 + 18, y2 + 33, fill="#b9c7dc", outline="")

            # Small decorative plaque at the front of the hotel
            plaque_x1 = w * 0.60
            plaque_y1 = h * 0.67
            plaque_x2 = w * 0.90
            plaque_y2 = h * 0.73
            canvas.create_rectangle(plaque_x1, plaque_y1, plaque_x2, plaque_y2, fill="#14365d", outline="#245287", width=2)
            canvas.create_line(plaque_x1 + 24, (plaque_y1 + plaque_y2) / 2, plaque_x2 - 24, (plaque_y1 + plaque_y2) / 2, fill="#60a5fa", width=3)

        canvas.bind("<Configure>", redraw)



    def handle_login(self):
        u, p = self.user_var.get().strip(), self.pass_var.get().strip()
        role = self.service.login(u, p)
        if role:
            self.role, self.username = role, u
            self.title(f"MingJin PMS - {self.role}")
            self.geometry("1400x850")
            try:
                self.state("zoomed")
            except tk.TclError:
                pass
            self.build_main_app()
        else:
            Messagebox.show_error("Sai tài khoản hoặc mật khẩu!", "Lỗi đăng nhập")

    def handle_logout(self):
        try:
            self.state("normal")
        except tk.TclError:
            pass
        self.title("MingJin PMS - Hệ thống quản lý khách sạn")
        self.show_login_screen()

    # =====================================================
    #  MAIN LAYOUT
    # =====================================================
    def build_main_app(self):
        self.clear_window()
        self.configure(bg=self.colors["bg"])

        style = tb.Style()
        style.configure(".", font=("Segoe UI", 10))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=36, background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#f8fafc", foreground="#475569")
        style.map("Treeview", background=[("selected", "#fff7ed")], foreground=[("selected", "#0f172a")])

        self.frames = {}
        self.menu_buttons = {}
        self._build_layout()
        self.switch_frame("Dashboard")
        self.show_toast("Đăng nhập thành công", f"Xin chào {self.role} {self.username}!", "success")

    def _build_layout(self):
        self.sidebar = tk.Frame(self, bg=self.colors["navy"], width=252)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=self.colors["navy"], padx=22, pady=26)
        brand.pack(fill=X)
        tk.Label(brand, text="MingJin PMS", bg=self.colors["navy"], fg="#ffffff", font=("Segoe UI", 17, "bold")).pack(anchor=W)
        tk.Label(brand, text="Hệ thống quản lý", bg=self.colors["navy"], fg="#9fb3cc", font=("Segoe UI", 10)).pack(anchor=W, pady=(4, 0))

        menus = [
            ("Dashboard", "Tổng quan"),
            ("Reception", "Đăng ký"),
            ("Rooms", "Phòng"),
            ("Messages", "Tin nhắn"),
            ("Housekeeping", "Dọn dẹp"),
            ("Inventory", "Kho vật tư"),
            ("Calendar", "Lịch trình"),
            ("Financials", "Tài chính"),
            ("Reviews", "Đánh giá"),
            ("Concierge", "Hỗ trợ"),
        ]

        menu_holder = tk.Frame(self.sidebar, bg=self.colors["navy"])
        menu_holder.pack(fill=X, padx=12)
        for key, text in menus:
            btn = tk.Button(menu_holder, text=f"  {text}", anchor=W, relief=FLAT, bd=0, bg=self.colors["navy"], fg="#d7e1ef", activebackground=self.colors["navy_2"], activeforeground="#ffffff", cursor="hand2", font=("Segoe UI", 11, "bold"), command=lambda f=key: self.switch_frame(f))
            btn.pack(fill=X, pady=3, ipady=11)
            self.menu_buttons[key] = btn

        logout = tk.Button(self.sidebar, text="  Đăng xuất", anchor=W, relief=FLAT, bd=0, bg="#0b2139", fg="#ffffff", activebackground="#13375f", activeforeground="#ffffff", cursor="hand2", font=("Segoe UI", 11, "bold"), command=self.handle_logout)
        logout.pack(side=BOTTOM, fill=X, padx=16, pady=22, ipady=12)

        self.main = tk.Frame(self, bg=self.colors["bg"], padx=28, pady=24)
        self.main.pack(side=LEFT, fill=BOTH, expand=True)

        self.header = tk.Frame(self.main, bg=self.colors["bg"])
        self.header.pack(fill=X, pady=(0, 22))

        title_box = tk.Frame(self.header, bg=self.colors["bg"])
        title_box.pack(side=LEFT)
        self.lbl_title = tk.Label(title_box, text="Tổng Quan Hệ Thống", bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 28, "bold"))
        self.lbl_title.pack(anchor=W)
        self.lbl_subtitle = tk.Label(title_box, text="Cập nhật tình hình hoạt động kinh doanh của khách sạn", bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 10))
        self.lbl_subtitle.pack(anchor=W, pady=(2, 0))

        top_actions = tk.Frame(self.header, bg=self.colors["bg"])
        top_actions.pack(side=RIGHT)

        search_box = tk.Frame(top_actions, bg="#ffffff", highlightbackground=self.colors["border"], highlightthickness=1, padx=10)
        search_box.pack(side=LEFT, padx=(0, 12), ipady=3)
        self.global_search_var = tk.StringVar()
        global_search = tk.Entry(search_box, textvariable=self.global_search_var, relief=FLAT, bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 10), width=22)
        global_search.pack(side=LEFT, padx=(0, 8), pady=7)
        global_search.insert(0, "Tìm kiếm...")
        global_search.bind("<FocusIn>", lambda e: global_search.delete(0, END) if global_search.get() == "Tìm kiếm..." else None)
        global_search.bind("<Return>", lambda e: self.handle_global_search())
        tk.Button(search_box, text="Tìm", relief=FLAT, bd=0, bg="#ffffff", fg="#334155", cursor="hand2", command=self.handle_global_search).pack(side=LEFT)

        tk.Button(top_actions, text="Hôm nay, 26/05/2025  ▾", bg=self.colors["navy_2"], fg="#ffffff", activebackground=self.colors["navy"], activeforeground="#ffffff", relief=FLAT, bd=0, font=("Segoe UI", 10), padx=14, pady=9, cursor="hand2", command=self.show_today_summary).pack(side=LEFT, padx=(0, 12))
        tk.Button(top_actions, text="Cài đặt", bg=self.colors["navy_2"], fg="#ffffff", activebackground=self.colors["navy"], activeforeground="#ffffff", relief=FLAT, bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.open_account_manager).pack(side=LEFT, padx=4)
        tk.Button(top_actions, text="Thông báo", bg=self.colors["navy_2"], fg="#ffffff", activebackground=self.colors["navy"], activeforeground="#ffffff", relief=FLAT, bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.show_notifications).pack(side=LEFT, padx=4)

        profile = tk.Frame(top_actions, bg="#ffffff", padx=12, pady=6, highlightbackground=self.colors["border"], highlightthickness=1, cursor="hand2")
        profile.pack(side=LEFT, padx=(10, 0))
        tk.Label(profile, text=(self.username[0].upper() if self.username else "A"), bg=self.colors["orange"], fg="#ffffff", font=("Segoe UI", 13, "bold"), width=2).pack(side=LEFT, padx=(0, 8), ipady=4)
        ptxt = tk.Frame(profile, bg="#ffffff")
        ptxt.pack(side=LEFT)
        tk.Label(ptxt, text=self.username.capitalize(), bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(anchor=W)
        tk.Label(ptxt, text=self.role, bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 8)).pack(anchor=W)
        profile.bind("<Button-1>", lambda e: self.open_account_manager())

        self.container = tk.Frame(self.main, bg=self.colors["bg"])
        self.container.pack(fill=BOTH, expand=True)

        self._build_dashboard_frame()
        self._build_reception_frame()
        self._build_rooms_frame()
        self._build_messages_frame()
        self._build_housekeeping_frame()
        self._build_inventory_frame()
        self._build_calendar_frame()
        self._build_financials_frame()
        self._build_reviews_frame()
        self._build_concierge_frame()

        for frame in self.frames.values():
            self.apply_roboto_to_widget_tree(frame)
        self.apply_roboto_to_widget_tree(self.sidebar)
        self.apply_roboto_to_widget_tree(self.header)

    def handle_global_search(self):
        keyword = self.global_search_var.get().strip()
        if not keyword or keyword == "Tìm kiếm...":
            return Messagebox.show_info("Nhập từ khóa cần tìm kiếm.", "Tìm kiếm")
        self.switch_frame("Rooms")
        self.room_search_var.set(keyword)
        self.refresh_rooms()

    def show_today_summary(self):
        total, rented, empty, rev, bookings = self.get_live_dashboard_stats()
        message = (
            "Tổng quan hôm nay:\n\n"
            f"- Tổng phòng: {total}\n"
            f"- Lượt đăng ký: {bookings}\n"
            f"- Phòng đang sử dụng: {rented}\n"
            f"- Phòng trống: {empty}\n"
            f"- Doanh thu: {format_currency(rev)}"
        )
        Messagebox.show_info(message, "Tổng quan ngày")

    def switch_frame(self, frame_name):
        for frame in self.frames.values():
            frame.pack_forget()
        self.frames[frame_name].pack(fill=BOTH, expand=True)

        titles = {
            "Dashboard": ("Tổng Quan Hệ Thống", "Cập nhật tình hình hoạt động kinh doanh của khách sạn"),
            "Reception": ("Nghiệp Vụ Đăng Ký", "Tiếp nhận khách hàng và phân phòng nhanh chóng"),
            "Rooms": ("Sơ Đồ Phòng", "Theo dõi tình trạng phòng theo thời gian thực"),
            "Messages": ("Tin Nhắn Nội Bộ", "Trao đổi công việc giữa các bộ phận"),
            "Housekeeping": ("Quản Lý Dọn Dẹp", "Theo dõi lịch trình và trạng thái vệ sinh"),
            "Inventory": ("Kho Vật Tư", "Quản lý vật tư tiêu hao trong khách sạn"),
            "Calendar": ("Lịch Trình", "Theo dõi sự kiện và công việc quan trọng"),
            "Financials": ("Báo Cáo Tài Chính", "Tổng hợp thu chi và doanh thu"),
            "Reviews": ("Đánh Giá Khách Hàng", "Theo dõi phản hồi và mức độ hài lòng"),
            "Concierge": ("Dịch Vụ Hỗ Trợ", "Quản lý yêu cầu hỗ trợ của khách hàng"),
        }
        title, subtitle = titles.get(frame_name, ("Tổng Quan", ""))
        self.lbl_title.config(text=title)
        self.lbl_subtitle.config(text=subtitle)

        for name, btn in self.menu_buttons.items():
            if name == frame_name:
                btn.configure(bg=self.colors["orange"], fg="#ffffff", activebackground=self.colors["orange_2"])
            else:
                btn.configure(bg=self.colors["navy"], fg="#d7e1ef", activebackground=self.colors["navy_2"])

        refresh_map = {
            "Dashboard": self.refresh_dashboard,
            "Reception": self.refresh_reception,
            "Rooms": self.refresh_rooms,
            "Messages": self.refresh_messages,
            "Housekeeping": self.refresh_housekeeping,
            "Inventory": self.refresh_inventory,
            "Calendar": self.refresh_calendar,
            "Concierge": self.refresh_supports,
        }
        if frame_name in refresh_map:
            refresh_map[frame_name]()

    # =====================================================
    #  ACCOUNT MANAGER
    # =====================================================
    def open_account_manager(self):
        if getattr(self, "role", "") != "Quản lý":
            Messagebox.show_warning(
                "Chỉ tài khoản 'Quản lý' mới có quyền thiết lập hệ thống!",
                "Từ chối truy cập"
            )
            return

        modal = tb.Toplevel(self)
        modal.title("Quản Lý Người Dùng")
        modal.geometry("760x680")
        modal.minsize(760, 680)
        modal.resizable(False, False)
        modal.position_center()

        tk.Label(
            modal,
            text="DANH SÁCH TÀI KHOẢN",
            bg=modal.cget("bg"),
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 12))

        table_wrap = tk.Frame(modal, bg=modal.cget("bg"))
        table_wrap.pack(fill=X, padx=24)

        tree = ttk.Treeview(
            table_wrap,
            columns=("ID", "User", "Pass", "Role"),
            show="headings",
            height=7
        )
        cols = [
            ("ID", "ID", 70),
            ("User", "Tên đăng nhập", 180),
            ("Pass", "Mật khẩu", 170),
            ("Role", "Phân quyền", 160),
        ]
        for col, title, width in cols:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor=CENTER)
        tree.pack(fill=X)

        form_card = tk.Frame(
            modal,
            bg="#ffffff",
            padx=22,
            pady=18,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        form_card.pack(fill=BOTH, expand=True, padx=24, pady=16)
        form_card.columnconfigure(1, weight=1)

        id_var = tb.StringVar()
        u_var = tb.StringVar()
        p_var = tb.StringVar()
        r_var = tb.StringVar()

        for i, (label, var) in enumerate([
            ("Tên đăng nhập:", u_var),
            ("Mật khẩu:", p_var),
        ]):
            tk.Label(
                form_card,
                text=label,
                bg="#ffffff",
                fg=self.colors["text"],
                font=("Segoe UI", 11)
            ).grid(row=i, column=0, sticky=E, padx=(0, 12), pady=10)

            tb.Entry(form_card, textvariable=var).grid(
                row=i, column=1, sticky=EW, pady=10
            )

        tk.Label(
            form_card,
            text="Phân quyền:",
            bg="#ffffff",
            fg=self.colors["text"],
            font=("Segoe UI", 11)
        ).grid(row=2, column=0, sticky=E, padx=(0, 12), pady=10)

        ttk.Combobox(
            form_card,
            textvariable=r_var,
            values=["Quản lý", "Lễ tân"],
            state="readonly"
        ).grid(row=2, column=1, sticky=EW, pady=10)

        def load_data():
            for r in tree.get_children():
                tree.delete(r)
            for u in self.service.get_all_users():
                tree.insert("", "end", values=u)

        def on_select(e=None):
            sel = tree.selection()
            if sel:
                item = tree.item(sel[0])["values"]
                id_var.set(item[0])
                u_var.set(item[1])
                p_var.set(item[2])
                r_var.set(item[3])

        tree.bind("<<TreeviewSelect>>", on_select)
        load_data()

        current_id = None
        for u in self.service.get_all_users():
            if u[1] == self.username:
                current_id = u[0]

        def add_acc():
            try:
                self.service.add_user(u_var.get(), p_var.get(), r_var.get())
                self._sync_service_users_to_state_db()
                self._save_audit_log("ADD_USER", f"Thêm tài khoản {u_var.get()}")
                load_data()
                self.show_toast("Thành công", "Đã thêm tài khoản!", "success")
            except Exception as e:
                Messagebox.show_error(str(e), "Lỗi")

        def upd_acc():
            if not id_var.get():
                return Messagebox.show_warning("Chọn tài khoản để sửa!", "Cảnh báo")
            try:
                self.service.update_user(id_var.get(), u_var.get(), p_var.get(), r_var.get())
                self._sync_service_users_to_state_db()
                self._save_audit_log("UPDATE_USER", f"Cập nhật tài khoản {u_var.get()}")
                load_data()
                self.show_toast("Thành công", "Đã cập nhật tài khoản!", "success")
                if str(current_id) == str(id_var.get()):
                    self.role = r_var.get()
                    self.username = u_var.get()
            except Exception as e:
                Messagebox.show_error(str(e), "Lỗi")

        def del_acc():
            if not id_var.get():
                return Messagebox.show_warning("Chọn tài khoản để xóa!", "Cảnh báo")
            if u_var.get() == self.username:
                return Messagebox.show_error(
                    "Không thể tự xóa tài khoản đang đăng nhập!",
                    "Lỗi"
                )
            if Messagebox.yesno("Chắc chắn xóa tài khoản này?", "Xác nhận"):
                self.service.delete_user(id_var.get())
                self._sync_service_users_to_state_db()
                self._save_audit_log("DELETE_USER", f"Xóa tài khoản {u_var.get()}")
                load_data()
                self.show_toast("Thành công", "Đã xóa tài khoản!", "success")
                id_var.set("")
                u_var.set("")
                p_var.set("")
                r_var.set("")

        footer = tk.Frame(modal, bg=modal.cget("bg"))
        footer.pack(fill=X, padx=24, pady=(0, 20))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1)

        tb.Button(
            footer,
            text="Thêm mới",
            bootstyle="success",
            command=add_acc
        ).grid(row=0, column=0, sticky=EW, padx=6, ipady=6)

        tb.Button(
            footer,
            text="Cập nhật",
            bootstyle="info",
            command=upd_acc
        ).grid(row=0, column=1, sticky=EW, padx=6, ipady=6)

        tb.Button(
            footer,
            text="Xóa",
            bootstyle="danger",
            command=del_acc
        ).grid(row=0, column=2, sticky=EW, padx=6, ipady=6)

    # =====================================================
    #  DASHBOARD
    # =====================================================
    def _build_dashboard_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"])
        self.frames["Dashboard"] = f

        # ================= KPI CARDS =================
        cards = tk.Frame(f, bg=self.colors["bg"])
        cards.pack(fill=X, pady=(0, 16))
        for i in range(4):
            cards.columnconfigure(i, weight=1)

        self.lbl_card_booking = self._create_kpi_card(
            cards, 0, "▣", "Lượt Đăng Ký", "0",
            "▲ 20%  so với hôm qua", self.colors["blue"], self.colors["soft_blue"]
        )
        self.lbl_card_rented = self._create_kpi_card(
            cards, 1, "▤", "Phòng Đang Sử Dụng", "0",
            "▲ 15%  so với hôm qua", self.colors["teal"], self.colors["soft_green"]
        )
        self.lbl_card_empty = self._create_kpi_card(
            cards, 2, "▯", "Phòng Trống", "0",
            "▼ 20%  so với hôm qua", self.colors["orange"], self.colors["soft_orange"], down=True
        )
        self.lbl_card_rev = self._create_kpi_card(
            cards, 3, "◎", "Tổng Doanh Thu", "0 VNĐ",
            "▲ 12%  so với hôm qua", self.colors["purple"], self.colors["soft_purple"]
        )

        # ================= CHARTS =================
        analytics = tk.Frame(f, bg=self.colors["bg"])
        analytics.pack(fill=BOTH, expand=True, pady=(0, 16))
        analytics.columnconfigure(0, weight=1)
        analytics.columnconfigure(1, weight=1)
        analytics.rowconfigure(0, weight=1)

        chart_left = self.make_card(analytics, padx=18, pady=16)
        chart_left.grid(row=0, column=0, sticky=NSEW, padx=(0, 9))
        self._build_revenue_chart(chart_left)

        chart_right = self.make_card(analytics, padx=18, pady=16)
        chart_right.grid(row=0, column=1, sticky=NSEW, padx=(9, 0))
        self._build_source_chart(chart_right)

        # ================= TABLE =================
        table_card = self.make_card(f, padx=18, pady=14)
        table_card.pack(fill=BOTH, expand=True)

        top = tk.Frame(table_card, bg="#ffffff")
        top.pack(fill=X, pady=(0, 12))

        tk.Label(
            top,
            text="👥  Khách Hàng Vừa Giao Dịch",
            bg="#ffffff",
            fg=self.colors["text"],
            font=(self.font_family, 14, "bold")
        ).pack(side=LEFT)

        tb.Button(
            top,
            text="Xem tất cả  ›",
            bootstyle="light",
            command=self.open_all_transactions_modal,
            width=14
        ).pack(side=RIGHT)

        cols = ("Mã HĐ", "Tên Khách Hàng", "Loại Hàng", "Mã Hàng", "Thời Gian", "Trạng Thái")
        self.tree_dash = ttk.Treeview(table_card, columns=cols, show="headings", style="Treeview", height=5)
        for c, w in zip(cols, [110, 240, 180, 120, 190, 150]):
            self.tree_dash.heading(c, text=c)
            self.tree_dash.column(c, width=w, anchor=CENTER, stretch=True)
        self.tree_dash.pack(fill=BOTH, expand=True)

    def _create_kpi_card(self, parent, col, icon, title, value, trend, color, soft_bg, down=False):
        parent.columnconfigure(col, weight=1)
        card = self.make_card(parent, padx=16, pady=14)
        card.grid(row=0, column=col, padx=7, sticky=NSEW)

        body = tk.Frame(card, bg="#ffffff")
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(1, weight=1)

        icon_canvas = tk.Canvas(body, width=52, height=52, bg="#ffffff", highlightthickness=0)
        icon_canvas.grid(row=0, column=0, rowspan=2, sticky=NW, padx=(0, 12))
        icon_canvas.create_oval(4, 4, 48, 48, fill=soft_bg, outline="")
        icon_canvas.create_text(26, 26, text=icon, fill=color, font=(self.font_family, 15, "bold"))

        tk.Label(
            body,
            text=title,
            bg="#ffffff",
            fg="#334155",
            font=(self.font_family, 10, "bold")
        ).grid(row=0, column=1, sticky=W)

        lbl = tk.Label(
            body,
            text=value,
            bg="#ffffff",
            fg=self.colors["text"],
            font=(self.font_family, 22, "bold")
        )
        lbl.grid(row=1, column=1, sticky=W, pady=(3, 0))

        trend_color = self.colors["red"] if down else self.colors["green"]
        tk.Label(
            body,
            text=trend,
            bg="#ffffff",
            fg=trend_color,
            font=(self.font_family, 9, "bold")
        ).grid(row=2, column=0, columnspan=2, sticky=W, pady=(14, 0))

        spark = tk.Canvas(body, width=92, height=40, bg="#ffffff", highlightthickness=0)
        spark.grid(row=1, column=2, rowspan=2, sticky=E, padx=(8, 0))
        self._draw_dashboard_sparkline(spark, color)

        return lbl

    def _draw_dashboard_sparkline(self, canvas, color):
        points = [(4, 31), (14, 25), (24, 29), (34, 18), (44, 22), (54, 12), (64, 19), (74, 9), (86, 4)]
        flat = []
        for x, y in points:
            flat.extend([x, y])
        canvas.create_line(*flat, fill=color, width=2, smooth=True)

    def _build_revenue_chart(self, parent):
        header = tk.Frame(parent, bg="#ffffff")
        header.pack(fill=X, pady=(0, 8))

        tk.Label(
            header,
            text="▰  Tăng Trưởng Doanh Thu",
            bg="#ffffff",
            fg=self.colors["text"],
            font=(self.font_family, 14, "bold")
        ).pack(side=LEFT)

        tk.Label(
            header,
            text="5 tháng gần đây  ˅",
            bg="#f8fafc",
            fg="#334155",
            font=(self.font_family, 9),
            padx=12,
            pady=6,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        ).pack(side=RIGHT)

        fig, ax = plt.subplots(figsize=(6.6, 2.9), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        x_labels = ["T1", "T2", "T3", "T4", "T5"]
        y_vals = [10, 25, 20, 31, 28]
        x = list(range(len(x_labels)))

        ax.plot(x, y_vals, color=self.colors["orange"], marker="o", linewidth=2.6, markersize=7)
        ax.fill_between(x, y_vals, color=self.colors["orange"], alpha=0.13)

        for i, val in enumerate(y_vals):
            ax.text(i, val + 1.3, str(val), ha="center", fontsize=9, fontweight="bold", color=self.colors["text"])

        ax.set_ylim(0, 42)
        ax.set_yticks([0, 10, 20, 30, 40])
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels)
        ax.set_ylabel("Triệu VNĐ", color=self.colors["muted"], fontsize=9)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")
        ax.tick_params(colors="#475569")
        ax.grid(axis="y", linestyle="--", alpha=0.32)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def _build_source_chart(self, parent):
        header = tk.Frame(parent, bg="#ffffff")
        header.pack(fill=X, pady=(0, 8))

        tk.Label(
            header,
            text="◔  Nguồn Giao Dịch",
            bg="#ffffff",
            fg=self.colors["text"],
            font=(self.font_family, 14, "bold")
        ).pack(side=LEFT)

        tk.Label(
            header,
            text="Năm nay  ˅",
            bg="#f8fafc",
            fg="#334155",
            font=(self.font_family, 9),
            padx=12,
            pady=6,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        ).pack(side=RIGHT)

        body = tk.Frame(parent, bg="#ffffff")
        body.pack(fill=BOTH, expand=True)

        fig, ax = plt.subplots(figsize=(3.4, 2.8), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        values = [27, 12, 61]
        colors = ["#f97316", "#14b8a6", "#facc15"]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct="%1.0f%%",
            startangle=90,
            counterclock=False,
            pctdistance=0.72
        )
        for t in autotexts:
            t.set_color("#ffffff")
            t.set_fontweight("bold")
            t.set_fontsize(9)

        ax.add_artist(plt.Circle((0, 0), 0.56, fc="#ffffff"))
        ax.axis("equal")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=body)
        canvas.draw()
        canvas.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=True)

        legend = tk.Frame(body, bg="#ffffff")
        legend.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0), pady=(14, 0))

        rows = [
            ("Khác", "27%", "810.000 VNĐ", colors[0]),
            ("Nền tảng", "12%", "360.000 VNĐ", colors[1]),
            ("Trực tiếp", "61%", "1.830.000 VNĐ", colors[2]),
        ]
        for name, pct, money, col in rows:
            line = tk.Frame(legend, bg="#ffffff")
            line.pack(fill=X, pady=8)
            tk.Label(line, text="●", bg="#ffffff", fg=col, font=(self.font_family, 12)).pack(side=LEFT)
            tk.Label(line, text=name, bg="#ffffff", fg="#334155", font=(self.font_family, 10)).pack(side=LEFT, padx=8)
            tk.Label(line, text=pct, bg="#ffffff", fg="#475569", font=(self.font_family, 10, "bold"), width=6).pack(side=LEFT)
            tk.Label(line, text=money, bg="#ffffff", fg="#475569", font=(self.font_family, 10)).pack(side=RIGHT)

        total = tk.Frame(legend, bg="#f8fafc", highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=9)
        total.pack(fill=X, pady=(12, 0))
        tk.Label(total, text="Tổng", bg="#f8fafc", fg=self.colors["text"], font=(self.font_family, 10, "bold")).pack(side=LEFT)
        tk.Label(total, text="3.000.000 VNĐ", bg="#f8fafc", fg=self.colors["text"], font=(self.font_family, 10, "bold")).pack(side=RIGHT)

    def refresh_dashboard(self):
        total, rented, empty, rev, bookings = self.get_live_dashboard_stats()

        self.lbl_card_booking.config(text=str(bookings))
        self.lbl_card_rented.config(text=str(rented))
        self.lbl_card_empty.config(text=str(empty))
        self.lbl_card_rev.config(text=format_currency(rev))

        for row in self.tree_dash.get_children():
            self.tree_dash.delete(row)

        for item in self.transaction_history[:10]:
            self.tree_dash.insert(
                "",
                "end",
                values=(
                    item["invoice"],
                    item["customer"],
                    item["room_type"],
                    item["room_id"],
                    item["time"],
                    item["status"],
                ),
            )

    def open_all_transactions_modal(self):
        modal = tb.Toplevel(self)
        modal.title("Tất Cả Giao Dịch Khách Hàng")
        modal.geometry("1080x620")
        modal.minsize(980, 560)
        modal.position_center()

        wrapper = tk.Frame(modal, bg="#f5f7fb", padx=20, pady=18)
        wrapper.pack(fill=BOTH, expand=True)

        header = tk.Frame(wrapper, bg="#f5f7fb")
        header.pack(fill=X, pady=(0, 14))

        tk.Label(
            header,
            text="TẤT CẢ GIAO DỊCH KHÁCH HÀNG",
            bg="#f5f7fb",
            fg=self.colors["text"],
            font=(self.font_family, 18, "bold")
        ).pack(side=LEFT)

        search_box = tk.Frame(header, bg="#f5f7fb")
        search_box.pack(side=RIGHT)

        search_var = tk.StringVar()
        tb.Entry(search_box, textvariable=search_var, width=28).pack(side=LEFT, padx=(0, 8))

        card = tk.Frame(
            wrapper,
            bg="#ffffff",
            padx=14,
            pady=14,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        card.pack(fill=BOTH, expand=True)

        cols = ("Mã HĐ", "Tên Khách Hàng", "Loại Phòng", "Mã Phòng", "Thời Gian", "Trạng Thái", "Số Tiền")
        tree = ttk.Treeview(card, columns=cols, show="headings", style="Treeview")
        widths = [90, 230, 130, 110, 180, 130, 150]
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor=CENTER)

        ybar = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(card, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky=NSEW)
        ybar.grid(row=0, column=1, sticky=NS)
        xbar.grid(row=1, column=0, sticky=EW)
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)

        def money_text(value):
            try:
                return format_currency(float(value))
            except Exception:
                return "0 VNĐ"

        def load_rows(keyword=""):
            for row in tree.get_children():
                tree.delete(row)

            keyword = keyword.strip().lower()
            for item in self.transaction_history:
                blob = (
                    f"{item.get('invoice', '')} "
                    f"{item.get('customer', '')} "
                    f"{item.get('room_type', '')} "
                    f"{item.get('room_id', '')} "
                    f"{item.get('time', '')} "
                    f"{item.get('status', '')} "
                    f"{item.get('amount', '')}"
                ).lower()

                if keyword and keyword not in blob:
                    continue

                tree.insert(
                    "",
                    "end",
                    values=(
                        item.get("invoice", ""),
                        item.get("customer", ""),
                        item.get("room_type", ""),
                        item.get("room_id", ""),
                        item.get("time", ""),
                        item.get("status", ""),
                        money_text(item.get("amount", 0)),
                    ),
                )

        def search():
            load_rows(search_var.get())

        tb.Button(search_box, text="Tìm", bootstyle="primary", command=search, width=8).pack(side=LEFT, padx=(0, 8))
        tb.Button(search_box, text="Làm mới", bootstyle="secondary", command=lambda: load_rows(""), width=10).pack(side=LEFT)

        footer = tk.Frame(wrapper, bg="#f5f7fb")
        footer.pack(fill=X, pady=(14, 0))

        total_lbl = tk.Label(
            footer,
            text=f"Tổng số giao dịch: {len(self.transaction_history)}",
            bg="#f5f7fb",
            fg=self.colors["muted"],
            font=(self.font_family, 10, "bold")
        )
        total_lbl.pack(side=LEFT, padx=(0, 12))

        def show_selected_detail():
            sel = tree.selection()
            if not sel:
                return Messagebox.show_warning(
                    "Vui lòng chọn một giao dịch để xem chi tiết!",
                    "Chưa chọn dữ liệu"
                )
            values = tree.item(sel[0])["values"]
            detail_message = (
                f"Mã hóa đơn: {values[0]}\n"
                f"Khách hàng: {values[1]}\n"
                f"Loại phòng: {values[2]}\n"
                f"Mã phòng: {values[3]}\n"
                f"Thời gian: {values[4]}\n"
                f"Trạng thái: {values[5]}\n"
                f"Số tiền: {values[6]}"
            )
            Messagebox.show_info(detail_message, "Chi tiết giao dịch")

        tb.Button(footer, text="Xem chi tiết", bootstyle="info", command=show_selected_detail, width=14).pack(side=RIGHT, padx=(8, 0))
        tb.Button(footer, text="Đóng", bootstyle="secondary", command=modal.destroy, width=12).pack(side=RIGHT)

        load_rows()

    # =====================================================
    #  RECEPTION
    # =====================================================
    def _build_reception_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"])
        self.frames["Reception"] = f
        self.cus_name = tb.StringVar()
        self.cus_cmnd = tb.StringVar()
        self.cus_phone = tb.StringVar()
        self.selected_room = tb.StringVar()
        stats = tk.Frame(f, bg=self.colors["bg"])
        stats.pack(fill=X, pady=(0, 14))
        self.recep_stat_empty = self.create_stat_card(stats, 0, "Phòng trống", "0", self.colors["green"], self.colors["soft_green"])
        self.recep_stat_used = self.create_stat_card(stats, 1, "Đang sử dụng", "0", self.colors["orange"], self.colors["soft_orange"])
        self.recep_stat_booking = self.create_stat_card(stats, 2, "Lượt đăng ký", "0", self.colors["blue"], self.colors["soft_blue"])
        body = tk.Frame(f, bg=self.colors["bg"])
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(0, weight=3); body.columnconfigure(1, weight=2); body.rowconfigure(0, weight=1)
        form_card = self.make_card(body, padx=26, pady=22)
        form_card.grid(row=0, column=0, sticky=NSEW, padx=(0, 10), pady=(0, 14))
        tk.Label(form_card, text="Lập Phiếu Đăng Ký", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 18, "bold")).pack(anchor=W, pady=(0, 6))
        tk.Label(form_card, text="Nhập thông tin khách hàng và chọn phòng còn trống để tiếp nhận.", bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor=W, pady=(0, 18))
        form_grid = tk.Frame(form_card, bg="#ffffff")
        form_grid.pack(fill=X)
        form_grid.columnconfigure(1, weight=1)
        for i, (label, var) in enumerate([("Tên Khách Hàng:", self.cus_name), ("CMND/CCCD:", self.cus_cmnd), ("Số Điện Thoại:", self.cus_phone)]):
            tk.Label(form_grid, text=label, bg="#ffffff", fg="#334155", font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky=E, padx=(0, 14), pady=10)
            tb.Entry(form_grid, textvariable=var, font=("Segoe UI", 11)).grid(row=i, column=1, sticky=EW, pady=10, ipady=5)
        tk.Label(form_grid, text="Mã Phòng:", bg="#ffffff", fg="#334155", font=("Segoe UI", 11, "bold")).grid(row=3, column=0, sticky=E, padx=(0, 14), pady=10)
        self.combo_rooms = ttk.Combobox(form_grid, textvariable=self.selected_room, state="readonly", font=("Segoe UI", 11))
        self.combo_rooms.grid(row=3, column=1, sticky=EW, pady=10, ipady=5)
        self.combo_rooms.bind("<<ComboboxSelected>>", lambda e: self.update_selected_room_preview())
        btn_row = tk.Frame(form_card, bg="#ffffff")
        btn_row.pack(fill=X, pady=(18, 0))
        tb.Button(btn_row, text="XÁC NHẬN ĐĂNG KÝ", bootstyle="warning", command=self.handle_checkin).pack(side=LEFT, fill=X, expand=True, ipady=8)
        tb.Button(btn_row, text="Làm mới", bootstyle="secondary", command=self.reset_reception_form).pack(side=LEFT, padx=(10, 0), ipady=8)
        preview_card = self.make_card(body, padx=24, pady=22)
        preview_card.grid(row=0, column=1, sticky=NSEW, padx=(10, 0), pady=(0, 14))
        tk.Label(preview_card, text="Thông Tin Phòng Được Chọn", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor=W)
        tk.Label(preview_card, text="Hỗ trợ lễ tân theo dõi nhanh trước khi xác nhận đăng ký", bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor=W, pady=(4, 16))
        self.lbl_room_code = tk.Label(preview_card, text="Phòng: ---", bg="#ffffff", fg="#0f172a", font=("Segoe UI", 12, "bold")); self.lbl_room_code.pack(anchor=W, pady=4)
        self.lbl_room_type = tk.Label(preview_card, text="Loại phòng: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11)); self.lbl_room_type.pack(anchor=W, pady=4)
        self.lbl_room_price = tk.Label(preview_card, text="Giá phòng: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11)); self.lbl_room_price.pack(anchor=W, pady=4)
        self.lbl_room_status = tk.Label(preview_card, text="Trạng thái: Sẵn sàng", bg="#ffffff", fg=self.colors["green"], font=("Segoe UI", 11, "bold")); self.lbl_room_status.pack(anchor=W, pady=(4, 16))
        tk.Frame(preview_card, bg=self.colors["border"], height=1).pack(fill=X, pady=(4, 16))
        tk.Label(preview_card, text="Checklist tiếp nhận", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(0, 10))
        for c in ["Kiểm tra CMND/CCCD hợp lệ", "Xác nhận số điện thoại khách", "Chọn đúng loại phòng mong muốn", "Tư vấn giá phòng và thời gian lưu trú", "Hoàn tất thao tác nhận phòng"]:
            tk.Label(preview_card, text=f"- {c}", bg="#ffffff", fg="#475569", font=("Segoe UI", 10)).pack(anchor=W, pady=2)
        recent_card = self.make_card(f, padx=18, pady=14)
        recent_card.pack(fill=BOTH, expand=True)
        tk.Label(recent_card, text="Khách Hàng Vừa Đăng Ký", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 10))
        cols = ("Mã HĐ", "Tên Khách Hàng", "Loại Phòng", "Mã Phòng", "Thời Gian", "Trạng Thái")
        self.reception_tree = ttk.Treeview(recent_card, columns=cols, show="headings", style="Treeview")
        for c, w in zip(cols, [100, 220, 150, 110, 180, 140]):
            self.reception_tree.heading(c, text=c); self.reception_tree.column(c, width=w, anchor=CENTER)
        self.reception_tree.pack(fill=BOTH, expand=True)

    def reset_reception_form(self):
        self.cus_name.set(""); self.cus_cmnd.set(""); self.cus_phone.set(""); self.refresh_reception()

    def update_selected_room_preview(self):
        selected = self.selected_room.get().strip()
        room_info = getattr(self, "reception_room_map", {}).get(selected)
        if not room_info:
            self.lbl_room_code.config(text="Phòng: ---"); self.lbl_room_type.config(text="Loại phòng: ---"); self.lbl_room_price.config(text="Giá phòng: ---"); self.lbl_room_status.config(text="Trạng thái: Sẵn sàng", fg=self.colors["green"]); return
        room_id, room_type, price = room_info[0], room_info[1], room_info[2]
        self.lbl_room_code.config(text=f"Phòng: {room_id}"); self.lbl_room_type.config(text=f"Loại phòng: {room_type}"); self.lbl_room_price.config(text=f"Giá phòng: {format_currency(price)}"); self.lbl_room_status.config(text="Trạng thái: Có thể nhận phòng", fg=self.colors["green"])

    def refresh_reception(self):
        empty_rooms = [
            r for r in self.get_display_rooms()
            if self.normalize_room_status(r[3]) == "Trống"
        ]

        self.reception_room_map = {}
        room_values = []
        for r in empty_rooms:
            text = f"{r[0]} ({r[1]})"
            self.reception_room_map[text] = r
            room_values.append(text)

        self.combo_rooms["values"] = room_values
        self.selected_room.set(room_values[0] if room_values else "Không còn phòng trống")
        self.update_selected_room_preview()

        total, rented, empty, rev, bookings = self.get_live_dashboard_stats()
        self.recep_stat_empty.config(text=str(empty))
        self.recep_stat_used.config(text=str(rented))
        self.recep_stat_booking.config(text=str(bookings))

        for item in self.reception_tree.get_children():
            self.reception_tree.delete(item)

        for item in self.transaction_history[:10]:
            self.reception_tree.insert(
                "",
                "end",
                values=(
                    item["invoice"],
                    item["customer"],
                    item["room_type"],
                    item["room_id"],
                    item["time"],
                    item["status"],
                ),
            )

    def handle_checkin(self):
        try:
            name = self.cus_name.get().strip()
            cmnd = self.cus_cmnd.get().strip()
            phone = self.cus_phone.get().strip()
            room_text = self.selected_room.get().strip()

            if not name:
                raise Exception("Vui lòng nhập tên khách hàng!")
            if not cmnd:
                raise Exception("Vui lòng nhập CMND/CCCD!")
            if not phone:
                raise Exception("Vui lòng nhập số điện thoại!")
            if not room_text or room_text == "Không còn phòng trống":
                raise Exception("Hiện không còn phòng trống để đăng ký!")

            validate_cmnd(cmnd)

            room_info = self.reception_room_map.get(room_text)
            if not room_info:
                raise Exception("Không tìm thấy thông tin phòng đã chọn!")

            room_id = str(room_info[0])
            room_type = room_info[1]
            room_price = float(room_info[2])

            self.room_status_overrides[room_id] = "Đang sử dụng"

            invoice = self._next_invoice_id()
            record = {
                "invoice": invoice,
                "customer": name,
                "room_type": room_type,
                "room_id": room_id,
                "time": self._now_str(),
                "status": "Đang ở",
                "amount": room_price,
            }

            self.active_stays[room_id] = record
            self.transaction_history.insert(0, record)
            self._save_room_state(room_id, "Đang sử dụng")
            self._save_transaction(record)
            self._save_customer_and_booking(name, cmnd, phone, room_id, room_price, "Đang ở")
            self._save_audit_log("CHECK_IN", f"Khách {name} nhận phòng {room_id}")

            try:
                self.service.check_in(room_id, name, cmnd, phone)
            except Exception:
                pass

            self.show_toast(
                "Thành công",
                f"Đã đăng ký phòng {room_id} cho khách {name}.",
                "success",
            )

            self.cus_name.set("")
            self.cus_cmnd.set("")
            self.cus_phone.set("")

            self.refresh_reception()
            self.refresh_dashboard()
            self.refresh_rooms()

        except Exception as e:
            Messagebox.show_error(str(e), "Lỗi đăng ký")

    # =====================================================
    #  ROOMS
    # =====================================================
    def _build_rooms_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"])
        self.frames["Rooms"] = f
        top_bar = tk.Frame(f, bg=self.colors["bg"]); top_bar.pack(fill=X, pady=(0, 12))
        left_title = tk.Frame(top_bar, bg=self.colors["bg"]); left_title.pack(side=LEFT)
        tk.Label(left_title, text="Quản Lý Sơ Đồ Phòng", bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 17, "bold")).pack(anchor=W)
        tk.Label(left_title, text="Phân cấp phòng theo tầng, trạng thái và nghiệp vụ vận hành", bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor=W, pady=(2, 0))
        self.room_filter_var = tk.StringVar(value="Tất cả")
        self.room_filter_buttons = {}
        filter_box = tk.Frame(top_bar, bg=self.colors["bg"]); filter_box.pack(side=RIGHT)
        for name in ["Tất cả", "Trống", "Đang sử dụng", "Bảo trì", "Cần dọn"]:
            btn = tk.Button(filter_box, text=name, relief=FLAT, bd=0, bg="#ffffff" if name != "Tất cả" else self.colors["orange"], fg="#334155" if name != "Tất cả" else "#ffffff", activebackground=self.colors["orange_2"], activeforeground="#ffffff", cursor="hand2", font=("Segoe UI", 9, "bold"), padx=12, pady=7, command=lambda n=name: self.set_room_filter(n))
            btn.pack(side=LEFT, padx=4); self.room_filter_buttons[name] = btn
        stat_bar = tk.Frame(f, bg=self.colors["bg"]); stat_bar.pack(fill=X, pady=(0, 12))
        self.room_stat_total = self.create_stat_card(stat_bar, 0, "Tổng phòng", "0", self.colors["blue"], self.colors["soft_blue"])
        self.room_stat_empty = self.create_stat_card(stat_bar, 1, "Phòng trống", "0", self.colors["green"], self.colors["soft_green"])
        self.room_stat_used = self.create_stat_card(stat_bar, 2, "Đang sử dụng", "0", self.colors["orange"], self.colors["soft_orange"])
        self.room_stat_floor = self.create_stat_card(stat_bar, 3, "Số tầng", "0", self.colors["purple"], self.colors["soft_purple"])
        tool_bar = self.make_card(f, padx=14, pady=12); tool_bar.pack(fill=X, pady=(0, 12))
        tk.Label(tool_bar, text="Chức năng nghiệp vụ phòng", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(side=LEFT, padx=(0, 14))
        self.lbl_selected_room = tk.Label(tool_bar, text="Chưa chọn phòng", bg="#fff7ed", fg=self.colors["orange"], font=("Segoe UI", 10, "bold"), padx=12, pady=7, highlightbackground="#fed7aa", highlightthickness=1)
        self.lbl_selected_room.pack(side=LEFT, padx=(0, 10))
        actions = [("Thêm phòng", self.open_add_room_modal, "info"), ("Nhận phòng", self.mark_room_used, "success"), ("Thanh toán", self.handle_checkout, "danger"), ("Bảo trì", self.mark_room_maintenance, "warning"), ("Cần dọn", self.mark_room_cleaning, "secondary"), ("Mở lại phòng", self.mark_room_empty, "primary"), ("Làm mới", self.refresh_rooms, "dark")]
        for text, cmd, style in actions:
            tb.Button(tool_bar, text=text, bootstyle=style, command=cmd, takefocus=False, cursor="hand2").pack(side=LEFT, padx=4, ipady=3)
        search_frame = tk.Frame(tool_bar, bg="#ffffff"); search_frame.pack(side=RIGHT)
        self.room_search_var = tk.StringVar()
        tb.Entry(search_frame, textvariable=self.room_search_var, width=24).pack(side=LEFT, padx=(0, 6), ipady=2)
        tb.Button(search_frame, text="Tìm", bootstyle="outline-primary", command=self.refresh_rooms).pack(side=LEFT)
        canvas_container = self.make_card(f, padx=0, pady=0); canvas_container.pack(fill=BOTH, expand=True)
        self.rooms_canvas = tk.Canvas(canvas_container, bg="#ffffff", highlightthickness=0)
        self.rooms_scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.rooms_canvas.yview)
        self.rooms_grid = tk.Frame(self.rooms_canvas, bg="#ffffff")
        self.rooms_grid.bind("<Configure>", lambda e: self.rooms_canvas.configure(scrollregion=self.rooms_canvas.bbox("all")))
        self.rooms_window = self.rooms_canvas.create_window((0, 0), window=self.rooms_grid, anchor="nw")
        self.rooms_canvas.configure(yscrollcommand=self.rooms_scrollbar.set)
        self.rooms_canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=18, pady=18)
        self.rooms_scrollbar.pack(side=RIGHT, fill=Y)
        self.rooms_canvas.bind("<Configure>", lambda e: self.rooms_canvas.itemconfig(self.rooms_window, width=e.width - 10))
        self.selected_room_id_for_checkout = None; self.selected_room_status = None; self.selected_card_widget = None

    def set_room_filter(self, filter_name):
        self.room_filter_var.set(filter_name)
        for name, btn in self.room_filter_buttons.items():
            btn.configure(bg=self.colors["orange"] if name == filter_name else "#ffffff", fg="#ffffff" if name == filter_name else "#334155")
        self.refresh_rooms()

    def get_room_floor(self, room_id):
        digits = "".join(ch for ch in str(room_id) if ch.isdigit())
        if len(digits) >= 3: return int(digits[:-2])
        if len(digits) >= 1: return int(digits[0])
        return 1

    def normalize_room_status(self, status):
        status = str(status).strip()
        low = status.lower()
        if low in ["dang su dung", "đang sử dụng", "đang xử lý", "occupied", "used"]: return "Đang sử dụng"
        if low in ["bao tri", "bảo trì", "maintenance"]: return "Bảo trì"
        if low in ["can don", "cần dọn", "dirty", "cleaning"]: return "Cần dọn"
        return "Trống" if status == "Trống" else status

    def get_display_rooms(self):
        db_rooms = list(self.service.get_all_rooms())
        room_map = {str(r[0]): (str(r[0]), r[1], r[2], self.normalize_room_status(r[3])) for r in db_rooms}
        demo_types = ["Standard", "Superior", "Deluxe", "VIP", "Suite", "Family"]
        demo_prices = {"Standard": 300000, "Superior": 450000, "Deluxe": 600000, "VIP": 800000, "Suite": 1200000, "Family": 950000}
        for floor in range(1, 7):
            for index in range(1, 9):
                room_id = f"{floor}{index:02d}"
                if room_id not in room_map:
                    r_type = demo_types[(floor + index) % len(demo_types)]
                    status = "Trống"
                    if (floor, index) in [(2, 3), (3, 6), (5, 2), (6, 7)]: status = "Đang sử dụng"
                    elif (floor, index) in [(4, 4), (6, 1)]: status = "Bảo trì"
                    elif (floor, index) in [(1, 5), (5, 6)]: status = "Cần dọn"
                    room_map[room_id] = (room_id, r_type, demo_prices[r_type], status)
        for room_id, status in self.room_status_overrides.items():
            if room_id in room_map:
                old = room_map[room_id]; room_map[room_id] = (old[0], old[1], old[2], status)
        return sorted(room_map.values(), key=lambda r: (self.get_room_floor(r[0]), str(r[0])))

    def refresh_rooms(self):
        self.selected_room_id_for_checkout = None; self.selected_room_status = None; self.selected_card_widget = None
        if hasattr(self, "lbl_selected_room"): self.lbl_selected_room.config(text="Chưa chọn phòng")
        for widget in self.rooms_grid.winfo_children(): widget.destroy()
        rooms = self.get_display_rooms()
        current_filter = self.room_filter_var.get()
        keyword = self.room_search_var.get().strip().lower()
        if current_filter != "Tất cả": rooms = [r for r in rooms if self.normalize_room_status(r[3]) == current_filter]
        if keyword: rooms = [r for r in rooms if keyword in str(r[0]).lower() or keyword in str(r[1]).lower() or keyword in str(r[3]).lower()]
        all_rooms = self.get_display_rooms()
        self.room_stat_total.config(text=str(len(all_rooms)))
        self.room_stat_empty.config(text=str(sum(1 for r in all_rooms if self.normalize_room_status(r[3]) == "Trống")))
        self.room_stat_used.config(text=str(sum(1 for r in all_rooms if self.normalize_room_status(r[3]) == "Đang sử dụng")))
        self.room_stat_floor.config(text=str(len(set(self.get_room_floor(r[0]) for r in all_rooms))))
        grouped = {}
        for r in rooms: grouped.setdefault(self.get_room_floor(r[0]), []).append(r)
        if not grouped:
            tk.Label(self.rooms_grid, text="Không tìm thấy phòng phù hợp.", bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 13, "bold")).pack(pady=40)
            return
        for floor in sorted(grouped.keys()):
            floor_frame = tk.Frame(self.rooms_grid, bg="#ffffff"); floor_frame.pack(fill=X, pady=(0, 18))
            floor_rooms = grouped[floor]
            floor_header = tk.Frame(floor_frame, bg="#f8fafc", padx=14, pady=10, highlightbackground=self.colors["border"], highlightthickness=1); floor_header.pack(fill=X)
            f_empty = sum(1 for r in floor_rooms if self.normalize_room_status(r[3]) == "Trống")
            f_used = sum(1 for r in floor_rooms if self.normalize_room_status(r[3]) == "Đang sử dụng")
            f_maintain = sum(1 for r in floor_rooms if self.normalize_room_status(r[3]) == "Bảo trì")
            f_clean = sum(1 for r in floor_rooms if self.normalize_room_status(r[3]) == "Cần dọn")
            tk.Label(floor_header, text=f"Tầng {floor}", bg="#f8fafc", fg=self.colors["text"], font=("Segoe UI", 14, "bold")).pack(side=LEFT)
            tk.Label(floor_header, text=f"  Tổng {len(floor_rooms)} | Trống {f_empty} | Đang sử dụng {f_used} | Bảo trì {f_maintain} | Cần dọn {f_clean}", bg="#f8fafc", fg=self.colors["muted"], font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=12)
            grid = tk.Frame(floor_frame, bg="#ffffff", padx=2, pady=8); grid.pack(fill=X)
            for index, r in enumerate(floor_rooms):
                row, col = index // 8, index % 8
                self._create_room_card(grid, row, col, r[0], r[1], r[2], self.normalize_room_status(r[3]))

    def _create_room_card(self, parent, row, col, r_id, r_type, price, status):
        status_style = {"Trống": (self.colors["green"], "#ecfdf5", "#065f46"), "Đang sử dụng": (self.colors["red"], "#fef2f2", "#991b1b"), "Bảo trì": ("#f59e0b", "#fffbeb", "#92400e"), "Cần dọn": ("#3b82f6", "#eff6ff", "#1e40af")}
        accent, soft, text = status_style.get(status, (self.colors["muted"], "#f8fafc", "#334155"))
        parent.columnconfigure(col, weight=1)
        card = tk.Frame(parent, bg=soft, padx=10, pady=9, highlightbackground=self.colors["border"], highlightthickness=1, cursor="hand2")
        card.grid(row=row, column=col, padx=6, pady=6, sticky=NSEW)
        tk.Label(card, text=str(r_id), bg=soft, fg=self.colors["text"], font=("Segoe UI", 15, "bold")).pack(anchor=W)
        tk.Label(card, text=str(r_type), bg=soft, fg="#475569", font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(2, 0))
        tk.Label(card, text=status.upper(), bg=soft, fg=text, font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(8, 0))
        tk.Frame(card, bg=accent, height=3).pack(fill=X, pady=(8, 5))
        tk.Label(card, text=format_currency(price), bg=soft, fg="#475569", font=("Segoe UI", 9)).pack(anchor=W)
        def on_click(e):
            if self.selected_card_widget: self.selected_card_widget.configure(highlightbackground=self.colors["border"], highlightthickness=1)
            card.configure(highlightbackground=self.colors["orange"], highlightthickness=2)
            self.selected_card_widget = card; self.selected_room_id_for_checkout = r_id; self.selected_room_status = status
            if hasattr(self, "lbl_selected_room"): self.lbl_selected_room.config(text=f"Đang chọn: Phòng {r_id} - {status}")
        for w in [card] + card.winfo_children(): w.bind("<Button-1>", on_click)

    def mark_room_maintenance(self): self._set_selected_room_status("Bảo trì", "Phòng đã chuyển sang trạng thái Bảo trì.", "warning")
    def mark_room_cleaning(self): self._set_selected_room_status("Cần dọn", "Đã gửi yêu cầu dọn phòng.", "info")
    def mark_room_empty(self): self._set_selected_room_status("Trống", "Phòng đã chuyển về trạng thái Trống.", "success")
    def mark_room_used(self):
        self.open_reception_for_selected_room()

    def open_reception_for_selected_room(self):
        if not getattr(self, "selected_room_id_for_checkout", None):
            return Messagebox.show_warning(
                "Vui lòng click chọn một phòng trống trước khi nhận phòng!",
                "Chưa chọn phòng"
            )

        room_id = str(self.selected_room_id_for_checkout)
        room_status = self.normalize_room_status(getattr(self, "selected_room_status", ""))

        if room_status != "Trống":
            message = "Phòng {} hiện đang ở trạng thái '{}', không thể nhận phòng trực tiếp.\n\nVui lòng chọn một phòng Trống để chuyển sang nghiệp vụ đăng ký.".format(room_id, room_status)
            return Messagebox.show_warning(message, "Không thể nhận phòng")

        room_info = self.get_room_info_by_id(room_id)
        if not room_info:
            return Messagebox.show_error("Không tìm thấy thông tin phòng đã chọn!", "Lỗi")

        room_text = f"{room_info[0]} ({room_info[1]})"

        self.switch_frame("Reception")
        self.refresh_reception()

        values = list(self.combo_rooms["values"])
        if room_text in values:
            self.selected_room.set(room_text)
            self.update_selected_room_preview()

        try:
            self.combo_rooms.focus_set()
        except Exception:
            pass

        self.show_toast(
            "Chuyển sang đăng ký",
            f"Đã chọn sẵn phòng {room_id}. Vui lòng nhập thông tin khách hàng để nhận phòng.",
            "info"
        )

    def _set_selected_room_status(self, status, message, style):
        if not getattr(self, "selected_room_id_for_checkout", None):
            return Messagebox.show_warning("Vui lòng click chọn một phòng bất kỳ trước!", "Chưa chọn phòng")
        room_id = str(self.selected_room_id_for_checkout)
        self.room_status_overrides[room_id] = status
        self.selected_room_status = status
        self._save_room_state(room_id, status)
        self.show_toast("Đã cập nhật", f"Phòng {room_id}: {message}", style)
        self.refresh_rooms()
        self.refresh_reception()
        self.refresh_dashboard()

    def open_add_room_modal(self):
        modal = tb.Toplevel(self)
        modal.title("Thêm Phòng Mới")
        modal.geometry("460x420")
        modal.minsize(460, 420)
        modal.resizable(False, False)
        modal.position_center()

        tk.Label(
            modal,
            text="KHAI BÁO PHÒNG MỚI",
            bg=modal.cget("bg"),
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=20)

        form = tk.Frame(
            modal,
            bg="#ffffff",
            padx=20,
            pady=20,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        form.pack(fill=BOTH, expand=True, padx=24, pady=(0, 16))
        form.columnconfigure(1, weight=1)

        id_var = tb.StringVar()
        type_var = tb.StringVar()
        price_var = tb.StringVar()

        tk.Label(form, text="Mã Phòng:", bg="#ffffff").grid(row=0, column=0, sticky=E, pady=10, padx=(0, 10))
        tb.Entry(form, textvariable=id_var).grid(row=0, column=1, sticky=EW, pady=10)

        tk.Label(form, text="Loại Phòng:", bg="#ffffff").grid(row=1, column=0, sticky=E, pady=10, padx=(0, 10))
        cb = ttk.Combobox(
            form,
            textvariable=type_var,
            state="readonly",
            values=["Standard", "VIP", "Suite", "Family", "Deluxe", "Superior"]
        )
        cb.current(0)
        cb.grid(row=1, column=1, sticky=EW, pady=10)

        tk.Label(form, text="Giá Tiền:", bg="#ffffff").grid(row=2, column=0, sticky=E, pady=10, padx=(0, 10))
        tb.Entry(form, textvariable=price_var).grid(row=2, column=1, sticky=EW, pady=10)

        def save_room():
            try:
                r_id = id_var.get().strip()
                r_type = type_var.get()
                price = float(price_var.get())
                if not r_id:
                    raise Exception("Vui lòng nhập Mã Phòng!")
                self.service.add_room(r_id, r_type, price)
                self._save_room_master(r_id, r_type, price, "Phòng được thêm từ giao diện quản lý")
                self.show_toast("Thành Công", f"Đã thêm phòng {r_id}!", "success")
                modal.destroy()
                self.refresh_rooms()
                self.refresh_reception()
            except ValueError:
                Messagebox.show_error("Giá tiền phải là số!", "Lỗi")
            except Exception as e:
                Messagebox.show_error(str(e), "Lỗi Hệ Thống")

        footer = tk.Frame(modal, bg=modal.cget("bg"))
        footer.pack(fill=X, padx=24, pady=(0, 20))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)

        tb.Button(
            footer,
            text="Lưu Thông Tin",
            bootstyle="success",
            command=save_room
        ).grid(row=0, column=0, sticky=EW, padx=(0, 6), ipady=6)

        tb.Button(
            footer,
            text="Đóng",
            bootstyle="secondary",
            command=modal.destroy
        ).grid(row=0, column=1, sticky=EW, padx=(6, 0), ipady=6)

    def handle_checkout(self):
        if not getattr(self, "selected_room_id_for_checkout", None):
            return Messagebox.show_warning(
                "Vui lòng click chọn một phòng bất kỳ trước!",
                "Chưa chọn phòng"
            )

        room_id = str(self.selected_room_id_for_checkout)

        if self.selected_room_status == "Trống":
            return Messagebox.show_info(
                "Phòng này đang trống, không cần thanh toán!",
                "Thông báo"
            )

        if not Messagebox.yesno(f"Xác nhận thanh toán phòng {room_id}?", "Thanh Toán"):
            return

        try:
            room_info = self.get_room_info_by_id(room_id)
            room_price = float(room_info[2]) if room_info else 0

            stay = self.active_stays.pop(room_id, None)
            amount = float(stay["amount"]) if stay else room_price

            self.total_revenue += amount
            self.add_financial_transaction(
                "THU",
                amount,
                f"Thanh toán phòng {room_id}",
                source="Thanh toán phòng",
                affects_revenue=False,
            )

            updated = False
            for item in self.transaction_history:
                if str(item["room_id"]) == room_id and item["status"] in ["Đang ở", "Đang sử dụng"]:
                    item["status"] = "Đã Trả"
                    item["time"] = self._now_str()
                    item["amount"] = amount
                    updated = True
                    break

            if not updated:
                self.transaction_history.insert(0, {
                    "invoice": self._next_invoice_id(),
                    "customer": "Khách lẻ",
                    "room_type": room_info[1] if room_info else "Standard",
                    "room_id": room_id,
                    "time": self._now_str(),
                    "status": "Đã Trả",
                    "amount": amount,
                })

            self.room_status_overrides[room_id] = "Trống"
            self._save_room_state(room_id, "Trống")
            self._save_all_transactions()
            self._close_booking_for_room(room_id, amount)
            self._save_audit_log("CHECK_OUT", f"Thanh toán phòng {room_id}, số tiền {amount}")

            try:
                db_room_ids = [str(r[0]) for r in self.service.get_all_rooms()]
                if room_id in db_room_ids:
                    self.service.check_out(room_id)
            except Exception:
                pass

            self.selected_room_id_for_checkout = None
            self.selected_room_status = None
            self.selected_card_widget = None

            self.show_toast(
                "Hoàn tất",
                f"Phòng {room_id} đã thanh toán. Doanh thu cộng thêm {format_currency(amount)}.",
                "success"
            )

            self.refresh_rooms()
            self.refresh_reception()
            self.refresh_dashboard()

        except Exception as e:
            Messagebox.show_error(str(e), "Lỗi thanh toán")

    # =====================================================
    #  MESSAGES
    # =====================================================
    def _build_messages_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"]); self.frames["Messages"] = f
        if not hasattr(self, "message_data"):
            self.message_data = [
                {"sender": "Lễ tân - Hà", "title": "Yêu cầu kiểm tra phòng 203", "time": "10:30 AM", "status": "Chưa đọc", "priority": "Cao", "content": "Khách phản ánh điều hòa phòng 203 hoạt động không ổn định. Nhờ bộ phận kỹ thuật kiểm tra sớm."},
                {"sender": "Housekeeping", "title": "Hoàn tất dọn phòng 105", "time": "09:45 AM", "status": "Đã đọc", "priority": "Thường", "content": "Phòng 105 đã được dọn dẹp xong và sẵn sàng tiếp nhận khách mới."},
                {"sender": "Kho vật tư", "title": "Cần bổ sung khăn tắm", "time": "08:20 AM", "status": "Chưa đọc", "priority": "Trung bình", "content": "Số lượng khăn tắm tại tầng 4 đang giảm. Đề nghị cấp bổ sung trong ca sáng."},
            ]
        stats, left, left_top, right = self.create_module_shell(f, [("Tổng tin nhắn", self.colors["blue"], self.colors["soft_blue"]), ("Chưa đọc", self.colors["orange"], self.colors["soft_orange"]), ("Ưu tiên cao", self.colors["red"], self.colors["soft_red"])], "Hộp Thư Nội Bộ", "Chi Tiết Tin Nhắn", "Xem nội dung và xử lý nhanh các thông báo nội bộ")
        self.msg_stat_total, self.msg_stat_unread, self.msg_stat_priority = stats
        actions = tk.Frame(left_top, bg="#ffffff"); actions.pack(side=RIGHT)
        self.msg_search_var = tk.StringVar(); tb.Entry(actions, textvariable=self.msg_search_var, width=22).pack(side=LEFT, padx=(0, 8))
        for text, style, cmd in [("Tìm", "outline-primary", self.search_messages), ("Thêm", "success", lambda: self.open_message_modal("add")), ("Sửa", "info", lambda: self.open_message_modal("edit")), ("Đã đọc", "warning", self.mark_message_read), ("Xóa", "danger", self.delete_selected_message)]:
            tb.Button(actions, text=text, bootstyle=style, command=cmd).pack(side=LEFT, padx=3)
        cols = ("Người Gửi", "Tiêu Đề", "Thời Gian", "Trạng Thái")
        self.tree_messages = ttk.Treeview(left, columns=cols, show="headings", style="Treeview")
        for c, w in zip(cols, [190, 320, 120, 120]): self.tree_messages.heading(c, text=c); self.tree_messages.column(c, width=w, anchor=CENTER)
        self.tree_messages.pack(fill=BOTH, expand=True); self.tree_messages.bind("<<TreeviewSelect>>", self.on_message_select)
        self.msg_sender_lbl = tk.Label(right, text="Người gửi: ---", bg="#ffffff", fg="#0f172a", font=("Segoe UI", 11, "bold")); self.msg_sender_lbl.pack(anchor=W, pady=4)
        self.msg_title_lbl = tk.Label(right, text="Tiêu đề: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11)); self.msg_title_lbl.pack(anchor=W, pady=4)
        self.msg_time_lbl = tk.Label(right, text="Thời gian: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11)); self.msg_time_lbl.pack(anchor=W, pady=4)
        self.msg_status_lbl = tk.Label(right, text="Trạng thái: ---", bg="#ffffff", fg=self.colors["orange"], font=("Segoe UI", 11, "bold")); self.msg_status_lbl.pack(anchor=W, pady=4)
        self.msg_priority_lbl = tk.Label(right, text="Mức độ ưu tiên: ---", bg="#ffffff", fg=self.colors["red"], font=("Segoe UI", 11, "bold")); self.msg_priority_lbl.pack(anchor=W, pady=(4, 16))
        tk.Label(right, text="Nội dung", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(0, 8))
        self.message_content = tk.Text(right, height=14, wrap="word", font=("Segoe UI", 10), relief=FLAT, bg="#f8fafc", fg="#334155", padx=12, pady=12); self.message_content.pack(fill=BOTH, expand=True)
        bottom = tk.Frame(right, bg="#ffffff"); bottom.pack(fill=X, pady=(12, 0))
        tb.Button(bottom, text="Đánh dấu đã đọc", bootstyle="warning", command=self.mark_message_read).pack(side=LEFT, padx=(0, 8))
        tb.Button(bottom, text="Chỉnh sửa", bootstyle="info", command=lambda: self.open_message_modal("edit")).pack(side=LEFT, padx=(0, 8))
        tb.Button(bottom, text="Xóa tin", bootstyle="danger", command=self.delete_selected_message).pack(side=LEFT)
        self.refresh_messages()

    def refresh_messages(self, keyword=""):
        self._refresh_message_like(self.tree_messages, self.message_data, keyword, lambda m: f"{m['sender']} {m['title']} {m['content']} {m['status']}", lambda m: (m["sender"], m["title"], m["time"], m["status"]))
        self.msg_stat_total.config(text=str(len(self.message_data))); self.msg_stat_unread.config(text=str(sum(1 for m in self.message_data if m["status"] == "Chưa đọc"))); self.msg_stat_priority.config(text=str(sum(1 for m in self.message_data if m["priority"] == "Cao")))
        self.msg_sender_lbl.config(text="Người gửi: ---"); self.msg_title_lbl.config(text="Tiêu đề: ---"); self.msg_time_lbl.config(text="Thời gian: ---"); self.msg_status_lbl.config(text="Trạng thái: ---", fg=self.colors["orange"]); self.msg_priority_lbl.config(text="Mức độ ưu tiên: ---", fg=self.colors["red"]); self._fill_text(self.message_content, "Chọn một tin nhắn ở danh sách bên trái để xem chi tiết.")

    def _refresh_message_like(self, tree, data, keyword, blob_fn, values_fn):
        for item in tree.get_children(): tree.delete(item)
        keyword = keyword.strip().lower()
        for idx, row in enumerate(data):
            if keyword and keyword not in blob_fn(row).lower(): continue
            tree.insert("", "end", iid=str(idx), values=values_fn(row))

    def on_message_select(self, event=None):
        sel = self.tree_messages.selection()
        if not sel: return
        idx = int(sel[0]); msg = self.message_data[idx]
        self.msg_sender_lbl.config(text=f"Người gửi: {msg['sender']}"); self.msg_title_lbl.config(text=f"Tiêu đề: {msg['title']}"); self.msg_time_lbl.config(text=f"Thời gian: {msg['time']}")
        self.msg_status_lbl.config(text=f"Trạng thái: {msg['status']}", fg=self.colors["green"] if msg["status"] == "Đã đọc" else self.colors["orange"])
        self.msg_priority_lbl.config(text=f"Mức độ ưu tiên: {msg['priority']}", fg=self.colors["red"] if msg["priority"] == "Cao" else self.colors["text"])
        self._fill_text(self.message_content, msg["content"])

    def search_messages(self): self.refresh_messages(self.msg_search_var.get().strip())

    def open_message_modal(self, mode="add"):
        self._open_generic_modal(
            title="THÔNG TIN TIN NHẮN", mode=mode, tree=self.tree_messages, data_list=self.message_data,
            fields=[("Người gửi", "sender"), ("Tiêu đề", "title"), ("Thời gian", "time")],
            combos=[("Trạng thái", "status", ["Chưa đọc", "Đã đọc"]), ("Ưu tiên", "priority", ["Thường", "Trung bình", "Cao"])],
            text_key="content", empty={"sender":"", "title":"", "time":"", "status":"Chưa đọc", "priority":"Thường", "content":""},
            refresh=self.refresh_messages, success_add="Đã thêm tin nhắn mới.", success_edit="Đã cập nhật tin nhắn."
        )

    def mark_message_read(self): self._set_selected_row_field(self.tree_messages, self.message_data, "status", "Đã đọc", self.refresh_messages, "Đã đánh dấu tin nhắn là đã đọc.")
    def delete_selected_message(self): self._delete_selected_row(self.tree_messages, self.message_data, self.refresh_messages, "tin nhắn")

    # =====================================================
    #  HOUSEKEEPING / INVENTORY / CALENDAR
    # =====================================================
    def _build_housekeeping_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"]); self.frames["Housekeeping"] = f
        if not hasattr(self, "housekeeping_data"):
            self.housekeeping_data = [
                {"area":"Phòng 101", "task":"Dọn phòng sau checkout", "staff":"Nguyễn Thị Mai", "shift":"Ca sáng", "priority":"Cao", "status":"Chờ xử lý", "note":"Khách vừa trả phòng, cần thay ga giường."},
                {"area":"Phòng 203", "task":"Bổ sung amenities", "staff":"Trần Thị Lan", "shift":"Ca chiều", "priority":"Trung bình", "status":"Đang thực hiện", "note":"Bổ sung khăn tắm, nước suối, bàn chải."},
                {"area":"Khu A", "task":"Dọn hành lang", "staff":"Nguyễn Thị Mai", "shift":"Ca sáng", "priority":"Thường", "status":"Hoàn thành", "note":"Đã vệ sinh hành lang và khu vực thang máy."},
            ]
        stats, left, top, right = self.create_module_shell(f, [("Tổng công việc", self.colors["blue"], self.colors["soft_blue"]), ("Chờ xử lý", self.colors["orange"], self.colors["soft_orange"]), ("Hoàn thành", self.colors["green"], self.colors["soft_green"])], "Lịch Trình Công Việc", "Chi Tiết Công Việc", "Theo dõi và xử lý nhanh các đầu việc vệ sinh")
        self.hk_stat_total, self.hk_stat_pending, self.hk_stat_done = stats
        self._build_housekeeping_content(left, top, right)
        self.refresh_housekeeping()

    def _build_housekeeping_content(self, left, top, right):
        toolbar = tk.Frame(left, bg="#ffffff")
        toolbar.pack(fill=X, pady=(0, 12))
        self.hk_search_var = tk.StringVar()
        tb.Entry(toolbar, textvariable=self.hk_search_var, width=20).pack(side=LEFT, padx=(0, 8))
        for text, style, cmd in [
            ("Tìm", "outline-primary", self.search_housekeeping),
            ("Thêm", "success", lambda: self.open_housekeeping_modal("add")),
            ("Sửa", "info", lambda: self.open_housekeeping_modal("edit")),
            ("Hoàn thành", "warning", self.mark_housekeeping_done),
            ("Xóa", "danger", self.delete_housekeeping_task),
        ]:
            tb.Button(toolbar, text=text, bootstyle=style, command=cmd, width=10).pack(side=LEFT, padx=3)
        cols=("Khu vực","Công việc","Nhân viên","Trạng thái"); self.tree_housekeeping=ttk.Treeview(left,columns=cols,show="headings",style="Treeview")
        for c,w in zip(cols,[160,280,180,140]): self.tree_housekeeping.heading(c,text=c); self.tree_housekeeping.column(c,width=w,anchor=CENTER)
        self.tree_housekeeping.pack(fill=BOTH,expand=True); self.tree_housekeeping.bind("<<TreeviewSelect>>",self.on_housekeeping_select)
        self.hk_area_lbl=tk.Label(right,text="Khu vực: ---",bg="#ffffff",fg="#0f172a",font=("Segoe UI",11,"bold")); self.hk_area_lbl.pack(anchor=W,pady=4)
        self.hk_task_lbl=tk.Label(right,text="Công việc: ---",bg="#ffffff",fg="#475569",font=("Segoe UI",11)); self.hk_task_lbl.pack(anchor=W,pady=4)
        self.hk_staff_lbl=tk.Label(right,text="Nhân viên: ---",bg="#ffffff",fg="#475569",font=("Segoe UI",11)); self.hk_staff_lbl.pack(anchor=W,pady=4)
        self.hk_shift_lbl=tk.Label(right,text="Ca làm: ---",bg="#ffffff",fg="#475569",font=("Segoe UI",11)); self.hk_shift_lbl.pack(anchor=W,pady=4)
        self.hk_priority_lbl=tk.Label(right,text="Ưu tiên: ---",bg="#ffffff",fg=self.colors["red"],font=("Segoe UI",11,"bold")); self.hk_priority_lbl.pack(anchor=W,pady=4)
        self.hk_status_lbl=tk.Label(right,text="Trạng thái: ---",bg="#ffffff",fg=self.colors["orange"],font=("Segoe UI",11,"bold")); self.hk_status_lbl.pack(anchor=W,pady=(4,16))
        tk.Label(right,text="Ghi chú",bg="#ffffff",fg=self.colors["text"],font=("Segoe UI",12,"bold")).pack(anchor=W,pady=(0,8))
        self.hk_note_text=tk.Text(right,height=12,wrap="word",font=("Segoe UI",10),relief=FLAT,bg="#f8fafc",fg="#334155",padx=12,pady=12); self.hk_note_text.pack(fill=BOTH,expand=True)

    def refresh_housekeeping(self, keyword=""):
        self._refresh_message_like(self.tree_housekeeping,self.housekeeping_data,keyword,lambda x:f"{x['area']} {x['task']} {x['staff']} {x['status']} {x['note']}",lambda x:(x["area"],x["task"],x["staff"],x["status"]))
        self.hk_stat_total.config(text=str(len(self.housekeeping_data))); self.hk_stat_pending.config(text=str(sum(1 for x in self.housekeeping_data if x["status"] in ["Chờ xử lý","Đang thực hiện"]))); self.hk_stat_done.config(text=str(sum(1 for x in self.housekeeping_data if x["status"]=="Hoàn thành")))
        self.hk_area_lbl.config(text="Khu vực: ---"); self.hk_task_lbl.config(text="Công việc: ---"); self.hk_staff_lbl.config(text="Nhân viên: ---"); self.hk_shift_lbl.config(text="Ca làm: ---"); self.hk_priority_lbl.config(text="Ưu tiên: ---",fg=self.colors["red"]); self.hk_status_lbl.config(text="Trạng thái: ---",fg=self.colors["orange"]); self._fill_text(self.hk_note_text,"Chọn một công việc ở bên trái để xem chi tiết.")

    def on_housekeeping_select(self,event=None):
        sel=self.tree_housekeeping.selection();
        if not sel: return
        i=int(sel[0]); x=self.housekeeping_data[i]
        self.hk_area_lbl.config(text=f"Khu vực: {x['area']}"); self.hk_task_lbl.config(text=f"Công việc: {x['task']}"); self.hk_staff_lbl.config(text=f"Nhân viên: {x['staff']}"); self.hk_shift_lbl.config(text=f"Ca làm: {x['shift']}"); self.hk_priority_lbl.config(text=f"Ưu tiên: {x['priority']}",fg=self.colors["red"] if x["priority"]=="Cao" else self.colors["text"]); self.hk_status_lbl.config(text=f"Trạng thái: {x['status']}",fg=self.colors["green"] if x["status"]=="Hoàn thành" else self.colors["orange"]); self._fill_text(self.hk_note_text,x["note"])
    def search_housekeeping(self): self.refresh_housekeeping(self.hk_search_var.get().strip())
    def mark_housekeeping_done(self): self._set_selected_row_field(self.tree_housekeeping,self.housekeeping_data,"status","Hoàn thành",self.refresh_housekeeping,"Đã cập nhật công việc sang trạng thái Hoàn thành.")
    def open_housekeeping_modal(self,mode="add"):
        self._open_generic_modal("THÔNG TIN CÔNG VIỆC",mode,self.tree_housekeeping,self.housekeeping_data,[("Khu vực","area"),("Công việc","task"),("Nhân viên","staff")],[("Ca làm","shift",["Ca sáng","Ca chiều","Ca tối"]),("Ưu tiên","priority",["Thường","Trung bình","Cao"]),("Trạng thái","status",["Chờ xử lý","Đang thực hiện","Hoàn thành"])],"note",{"area":"","task":"","staff":"","shift":"Ca sáng","priority":"Thường","status":"Chờ xử lý","note":""},self.refresh_housekeeping,"Đã thêm công việc mới.","Đã cập nhật công việc.")
    def delete_housekeeping_task(self): self._delete_selected_row(self.tree_housekeeping,self.housekeeping_data,self.refresh_housekeeping,"công việc")

    def _build_inventory_frame(self):
        f=tk.Frame(self.container,bg=self.colors["bg"]); self.frames["Inventory"]=f
        if not hasattr(self,"inventory_data"):
            self.inventory_data=[{"code":"VT001","name":"Giấy in A4","stock":150,"unit":"Ream","category":"Văn phòng phẩm","status":"An toàn","supplier":"Thiên Long","note":"Dùng cho lễ tân và kế toán."},{"code":"VT002","name":"Khăn tắm","stock":18,"unit":"Cái","category":"Buồng phòng","status":"Sắp hết","supplier":"Hotel Supply","note":"Cần nhập thêm trong tuần này."},{"code":"VT003","name":"Nước suối","stock":320,"unit":"Chai","category":"Minibar","status":"An toàn","supplier":"Lavie","note":"Phục vụ khách lưu trú."}]
        stats,left,top,right=self.create_module_shell(f,[("Tổng vật tư",self.colors["blue"],self.colors["soft_blue"]),("Sắp hết",self.colors["orange"],self.colors["soft_orange"]),("An toàn",self.colors["green"],self.colors["soft_green"])],"Quản Lý Kho","Chi Tiết Vật Tư","Theo dõi tồn kho và xử lý nhập / xuất nhanh")
        self.inv_stat_total,self.inv_stat_low,self.inv_stat_safe=stats
        toolbar = tk.Frame(left, bg="#ffffff")
        toolbar.pack(fill=X, pady=(0, 12))
        self.inv_search_var = tk.StringVar()
        tb.Entry(toolbar, textvariable=self.inv_search_var, width=18).pack(side=LEFT, padx=(0, 8))
        for text, style, cmd, width in [
            ("Tìm", "outline-primary", self.search_inventory, 8),
            ("Thêm", "success", lambda: self.open_inventory_modal("add"), 8),
            ("Sửa", "info", lambda: self.open_inventory_modal("edit"), 8),
            ("Nhập", "warning", self.open_import_stock_modal, 8),
            ("Xuất", "secondary", self.open_export_stock_modal, 8),
            ("Xóa", "danger", self.delete_inventory_item, 8),
        ]:
            tb.Button(toolbar, text=text, bootstyle=style, command=cmd, width=width).pack(side=LEFT, padx=2)
        cols=("Mã VT","Tên vật tư","Tồn kho","Đơn vị","Tình trạng"); self.tree_inventory=ttk.Treeview(left,columns=cols,show="headings",style="Treeview")
        for c,w in zip(cols,[100,240,100,100,130]): self.tree_inventory.heading(c,text=c); self.tree_inventory.column(c,width=w,anchor=CENTER)
        self.tree_inventory.pack(fill=BOTH,expand=True); self.tree_inventory.bind("<<TreeviewSelect>>",self.on_inventory_select)
        self.inv_labels={}
        for key,label,bold in [("code","Mã vật tư",True),("name","Tên vật tư",False),("stock","Số lượng tồn",False),("unit","Đơn vị",False),("category","Nhóm hàng",False),("supplier","Nhà cung cấp",False),("status","Tình trạng",True)]:
            lbl=tk.Label(right,text=f"{label}: ---",bg="#ffffff",fg=self.colors["orange"] if key=="status" else ("#0f172a" if bold else "#475569"),font=("Segoe UI",11,"bold" if bold else "normal")); lbl.pack(anchor=W,pady=4); self.inv_labels[key]=lbl
        tk.Label(right,text="Ghi chú",bg="#ffffff",fg=self.colors["text"],font=("Segoe UI",12,"bold")).pack(anchor=W,pady=(12,8)); self.inv_note_text=tk.Text(right,height=12,wrap="word",font=("Segoe UI",10),relief=FLAT,bg="#f8fafc",fg="#334155",padx=12,pady=12); self.inv_note_text.pack(fill=BOTH,expand=True)
        self.refresh_inventory()

    def update_inventory_status(self,item): item.__setitem__("status","Sắp hết" if int(item["stock"])<=20 else "An toàn")
    def refresh_inventory(self,keyword=""):
        for it in self.inventory_data: self.update_inventory_status(it)
        self._refresh_message_like(self.tree_inventory,self.inventory_data,keyword,lambda x:f"{x['code']} {x['name']} {x['category']} {x['status']} {x['supplier']}",lambda x:(x["code"],x["name"],x["stock"],x["unit"],x["status"]))
        self.inv_stat_total.config(text=str(len(self.inventory_data))); self.inv_stat_low.config(text=str(sum(1 for x in self.inventory_data if x["status"]=="Sắp hết"))); self.inv_stat_safe.config(text=str(sum(1 for x in self.inventory_data if x["status"]=="An toàn")))
        for key,lbl in self.inv_labels.items(): lbl.config(text=f"{ {'code':'Mã vật tư','name':'Tên vật tư','stock':'Số lượng tồn','unit':'Đơn vị','category':'Nhóm hàng','supplier':'Nhà cung cấp','status':'Tình trạng'}[key] }: ---")
        self._fill_text(self.inv_note_text,"Chọn một vật tư ở bên trái để xem chi tiết.")
    def on_inventory_select(self,event=None):
        sel=self.tree_inventory.selection();
        if not sel: return
        i=int(sel[0]); x=self.inventory_data[i]
        labels={'code':'Mã vật tư','name':'Tên vật tư','stock':'Số lượng tồn','unit':'Đơn vị','category':'Nhóm hàng','supplier':'Nhà cung cấp','status':'Tình trạng'}
        for key,lbl in self.inv_labels.items(): lbl.config(text=f"{labels[key]}: {x[key]}",fg=self.colors["green"] if key=="status" and x[key]=="An toàn" else (self.colors["orange"] if key=="status" else lbl.cget('fg')))
        self._fill_text(self.inv_note_text,x["note"])
    def search_inventory(self): self.refresh_inventory(self.inv_search_var.get().strip())
    def open_inventory_modal(self,mode="add"):
        self._open_generic_modal("THÔNG TIN VẬT TƯ",mode,self.tree_inventory,self.inventory_data,[("Mã vật tư","code"),("Tên vật tư","name"),("Số lượng tồn","stock"),("Đơn vị","unit"),("Nhóm hàng","category"),("Nhà cung cấp","supplier")],[],"note",{"code":"","name":"","stock":0,"unit":"Cái","category":"","status":"An toàn","supplier":"","note":""},self.refresh_inventory,"Đã thêm vật tư mới.","Đã cập nhật vật tư.",numeric_keys=["stock"],postprocess=self.update_inventory_status)
    def open_import_stock_modal(self): self._stock_adjust("import")
    def open_export_stock_modal(self): self._stock_adjust("export")
    def _stock_adjust(self,mode):
        sel=self.tree_inventory.selection();
        if not sel: return Messagebox.show_warning("Vui lòng chọn một vật tư trước!","Chưa chọn dữ liệu")
        idx=int(sel[0]); item=self.inventory_data[idx]; modal=tb.Toplevel(self); modal.title("Nhập kho" if mode=="import" else "Xuất kho"); modal.geometry("420x240"); modal.position_center(); tb.Label(modal,text=("NHẬP KHO" if mode=="import" else "XUẤT KHO")+f" - {item['name']}",font=("Segoe UI",14,"bold"),bootstyle="warning" if mode=="import" else "secondary").pack(pady=18)
        qty_var=tb.StringVar(); tb.Label(modal,text="Số lượng:").pack(anchor=W,padx=24); tb.Entry(modal,textvariable=qty_var).pack(fill=X,padx=24,ipady=4)
        def save():
            try:
                qty=int(qty_var.get().strip()); assert qty>0
                if mode=="export" and qty>int(item["stock"]): raise Exception
            except Exception: return Messagebox.show_warning("Số lượng không hợp lệ!","Lỗi")
            item["stock"] += qty if mode=="import" else -qty; self.update_inventory_status(item); self._save_all_inventory(); self.show_toast("Thành công","Đã cập nhật tồn kho.","success"); modal.destroy(); self.refresh_inventory()
        tb.Button(modal,text="Xác nhận",bootstyle="success",command=save).pack(fill=X,padx=24,pady=18,ipady=4)
    def delete_inventory_item(self): self._delete_selected_row(self.tree_inventory,self.inventory_data,self.refresh_inventory,"vật tư")

    def _build_calendar_frame(self):
        f=tk.Frame(self.container,bg=self.colors["bg"]); self.frames["Calendar"]=f
        if not hasattr(self,"calendar_data"):
            self.calendar_data=[{"date":"26/05/2025","time":"08:30","type":"Họp nội bộ","location":"Phòng họp A","person":"Ban quản lý","status":"Sắp diễn ra","note":"Họp giao ban đầu tuần."},{"date":"26/05/2025","time":"14:00","type":"Kiểm tra thiết bị","location":"Tầng 3","person":"Kỹ thuật","status":"Đang thực hiện","note":"Kiểm tra điều hòa và thiết bị điện."},{"date":"27/05/2025","time":"09:00","type":"Đón đoàn khách","location":"Sảnh chính","person":"Lễ tân","status":"Sắp diễn ra","note":"Chuẩn bị tiếp đón đoàn 12 khách."}]
        stats,left,top,right=self.create_module_shell(f,[("Tổng sự kiện",self.colors["blue"],self.colors["soft_blue"]),("Sắp diễn ra",self.colors["orange"],self.colors["soft_orange"]),("Đang thực hiện",self.colors["green"],self.colors["soft_green"])],"Lịch Trình Sự Kiện","Chi Tiết Sự Kiện","Theo dõi công việc và sự kiện quan trọng trong hệ thống")
        self.cal_stat_total,self.cal_stat_upcoming,self.cal_stat_progress=stats
        toolbar = tk.Frame(left, bg="#ffffff")
        toolbar.pack(fill=X, pady=(0, 12))
        self.cal_search_var = tk.StringVar()
        tb.Entry(toolbar, textvariable=self.cal_search_var, width=20).pack(side=LEFT, padx=(0, 8))
        for text, style, cmd in [
            ("Tìm", "outline-primary", self.search_calendar),
            ("Thêm", "success", lambda: self.open_calendar_modal("add")),
            ("Sửa", "info", lambda: self.open_calendar_modal("edit")),
            ("Hoàn tất", "warning", self.mark_calendar_done),
            ("Xóa", "danger", self.delete_calendar_item),
        ]:
            tb.Button(toolbar, text=text, bootstyle=style, command=cmd, width=9).pack(side=LEFT, padx=3)
        cols=("Ngày","Giờ","Loại sự kiện","Phụ trách","Trạng thái"); self.tree_calendar=ttk.Treeview(left,columns=cols,show="headings",style="Treeview")
        for c,w in zip(cols,[110,90,220,160,130]): self.tree_calendar.heading(c,text=c); self.tree_calendar.column(c,width=w,anchor=CENTER)
        self.tree_calendar.pack(fill=BOTH,expand=True); self.tree_calendar.bind("<<TreeviewSelect>>",self.on_calendar_select)
        self.cal_labels={}
        for key,label,bold in [("date","Ngày",True),("time","Giờ",False),("type","Loại sự kiện",False),("location","Địa điểm",False),("person","Phụ trách",False),("status","Trạng thái",True)]:
            lbl=tk.Label(right,text=f"{label}: ---",bg="#ffffff",fg=self.colors["orange"] if key=="status" else ("#0f172a" if bold else "#475569"),font=("Segoe UI",11,"bold" if bold else "normal")); lbl.pack(anchor=W,pady=4); self.cal_labels[key]=lbl
        tk.Label(right,text="Ghi chú",bg="#ffffff",fg=self.colors["text"],font=("Segoe UI",12,"bold")).pack(anchor=W,pady=(12,8)); self.cal_note_text=tk.Text(right,height=12,wrap="word",font=("Segoe UI",10),relief=FLAT,bg="#f8fafc",fg="#334155",padx=12,pady=12); self.cal_note_text.pack(fill=BOTH,expand=True)
        self.refresh_calendar()
    def refresh_calendar(self,keyword=""):
        self._refresh_message_like(self.tree_calendar,self.calendar_data,keyword,lambda x:f"{x['date']} {x['time']} {x['type']} {x['location']} {x['person']} {x['status']} {x['note']}",lambda x:(x["date"],x["time"],x["type"],x["person"],x["status"]))
        self.cal_stat_total.config(text=str(len(self.calendar_data))); self.cal_stat_upcoming.config(text=str(sum(1 for x in self.calendar_data if x["status"]=="Sắp diễn ra"))); self.cal_stat_progress.config(text=str(sum(1 for x in self.calendar_data if x["status"]=="Đang thực hiện")))
        labels={"date":"Ngày","time":"Giờ","type":"Loại sự kiện","location":"Địa điểm","person":"Phụ trách","status":"Trạng thái"}
        for k,l in self.cal_labels.items(): l.config(text=f"{labels[k]}: ---")
        self._fill_text(self.cal_note_text,"Chọn một sự kiện ở bên trái để xem chi tiết.")
    def on_calendar_select(self,event=None):
        sel=self.tree_calendar.selection();
        if not sel: return
        i=int(sel[0]); x=self.calendar_data[i]; labels={"date":"Ngày","time":"Giờ","type":"Loại sự kiện","location":"Địa điểm","person":"Phụ trách","status":"Trạng thái"}
        for k,l in self.cal_labels.items(): l.config(text=f"{labels[k]}: {x[k]}",fg=self.colors["green"] if k=="status" and x[k]=="Hoàn thành" else (self.colors["orange"] if k=="status" else l.cget('fg')))
        self._fill_text(self.cal_note_text,x["note"])
    def search_calendar(self): self.refresh_calendar(self.cal_search_var.get().strip())
    def mark_calendar_done(self): self._set_selected_row_field(self.tree_calendar,self.calendar_data,"status","Hoàn thành",self.refresh_calendar,"Đã cập nhật sự kiện sang trạng thái Hoàn thành.")
    def open_calendar_modal(self,mode="add"):
        self._open_generic_modal("THÔNG TIN SỰ KIỆN",mode,self.tree_calendar,self.calendar_data,[("Ngày","date"),("Giờ","time"),("Loại sự kiện","type"),("Địa điểm","location"),("Phụ trách","person")],[("Trạng thái","status",["Sắp diễn ra","Đang thực hiện","Hoàn thành"])],"note",{"date":"","time":"","type":"","location":"","person":"","status":"Sắp diễn ra","note":""},self.refresh_calendar,"Đã thêm sự kiện mới.","Đã cập nhật sự kiện.")
    def delete_calendar_item(self): self._delete_selected_row(self.tree_calendar,self.calendar_data,self.refresh_calendar,"sự kiện")

    # =====================================================
    #  GENERIC CRUD HELPERS
    # =====================================================
    def _set_selected_row_field(self, tree, data, key, value, refresh_fn, success_msg):
        sel=tree.selection()
        if not sel: return Messagebox.show_warning("Vui lòng chọn một dòng dữ liệu trước!","Chưa chọn dữ liệu")
        idx=int(sel[0]); data[idx][key]=value; self._save_module_by_tree(tree); self.show_toast("Thành công",success_msg,"success"); refresh_fn()
        try: tree.selection_set(str(idx))
        except Exception: pass

    def _delete_selected_row(self, tree, data, refresh_fn, item_name):
        sel=tree.selection()
        if not sel: return Messagebox.show_warning(f"Vui lòng chọn một {item_name} để xóa!","Chưa chọn dữ liệu")
        idx=int(sel[0])
        if Messagebox.yesno(f"Bạn có chắc chắn muốn xóa {item_name} này?","Xác nhận xóa"):
            del data[idx]; self._save_module_by_tree(tree); self.show_toast("Thành công",f"Đã xóa {item_name}.","success"); refresh_fn()

    def _open_generic_modal(
        self,
        title,
        mode,
        tree,
        data_list,
        fields,
        combos,
        text_key,
        empty,
        refresh,
        success_add,
        success_edit,
        numeric_keys=None,
        postprocess=None
    ):
        numeric_keys = numeric_keys or []
        edit_mode = mode == "edit"

        if edit_mode:
            sel = tree.selection()
            if not sel:
                return Messagebox.show_warning(
                    "Vui lòng chọn một dòng để chỉnh sửa!",
                    "Chưa chọn dữ liệu"
                )
            idx = int(sel[0])
            data = data_list[idx]
        else:
            idx = None
            data = empty.copy()

        modal = tb.Toplevel(self)
        modal.title(title)
        modal.geometry("680x780")
        modal.minsize(680, 780)
        modal.resizable(False, False)
        modal.position_center()

        tk.Label(
            modal,
            text=title,
            bg=modal.cget("bg"),
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 12))

        body = tk.Frame(modal, bg=modal.cget("bg"))
        body.pack(fill=BOTH, expand=False, padx=24)

        form = tk.Frame(
            body,
            bg="#ffffff",
            padx=18,
            pady=18,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        form.pack(fill=BOTH, expand=True)
        form.columnconfigure(1, weight=1)

        vars_map = {}
        row = 0

        for label, key in fields:
            vars_map[key] = tb.StringVar(value=str(data.get(key, "")))
            tk.Label(
                form,
                text=label + ":",
                bg="#ffffff",
                fg=self.colors["text"],
                font=("Segoe UI", 11)
            ).grid(row=row, column=0, sticky=E, padx=(0, 12), pady=9)
            tb.Entry(form, textvariable=vars_map[key]).grid(
                row=row, column=1, sticky=EW, pady=9
            )
            row += 1

        for label, key, values in combos:
            vars_map[key] = tb.StringVar(value=str(data.get(key, values[0] if values else "")))
            tk.Label(
                form,
                text=label + ":",
                bg="#ffffff",
                fg=self.colors["text"],
                font=("Segoe UI", 11)
            ).grid(row=row, column=0, sticky=E, padx=(0, 12), pady=9)
            ttk.Combobox(
                form,
                textvariable=vars_map[key],
                values=values,
                state="readonly"
            ).grid(row=row, column=1, sticky=EW, pady=9)
            row += 1

        tk.Label(
            form,
            text="Ghi chú/Nội dung:",
            bg="#ffffff",
            fg=self.colors["text"],
            font=("Segoe UI", 11)
        ).grid(row=row, column=0, sticky=NE, padx=(0, 12), pady=9)

        txt = tk.Text(
            form,
            height=5,
            font=("Segoe UI", 10),
            wrap="word"
        )
        txt.grid(row=row, column=1, sticky=EW, pady=9)
        txt.insert("1.0", data.get(text_key, ""))

        footer = tk.Frame(modal, bg=modal.cget("bg"))
        footer.pack(fill=X, padx=24, pady=(8, 18))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)

        def save():
            new_data = empty.copy()
            for key, var in vars_map.items():
                val = var.get().strip()
                if key in numeric_keys:
                    try:
                        val = int(val)
                    except Exception:
                        return Messagebox.show_warning(
                            "Giá trị số không hợp lệ!",
                            "Dữ liệu không hợp lệ"
                        )
                new_data[key] = val

            new_data[text_key] = txt.get("1.0", END).strip()
            required_keys = [key for _, key in fields[:3]]
            if any(not str(new_data.get(k, "")).strip() for k in required_keys):
                return Messagebox.show_warning(
                    "Vui lòng nhập đầy đủ thông tin!",
                    "Thiếu dữ liệu"
                )

            if postprocess:
                postprocess(new_data)

            if edit_mode:
                data_list[idx] = new_data
                self.show_toast("Thành công", success_edit, "success")
            else:
                data_list.insert(0, new_data)
                self.show_toast("Thành công", success_add, "success")

            self._save_module_by_tree(tree)
            modal.destroy()
            refresh()

        tb.Button(
            footer,
            text="Lưu dữ liệu",
            bootstyle="success",
            command=save
        ).grid(row=0, column=0, sticky=EW, padx=(0, 6), ipady=6)

        tb.Button(
            footer,
            text="Đóng",
            bootstyle="secondary",
            command=modal.destroy
        ).grid(row=0, column=1, sticky=EW, padx=(6, 0), ipady=6)

    # =====================================================
    #  OTHER MODULES
    # =====================================================
    def _create_modern_table(self, frame, title, columns, data, show_toolbar=True):
        container = self.make_card(frame, padx=18, pady=16)
        container.pack(fill=BOTH, expand=True, pady=10)
        top = tk.Frame(container, bg="#ffffff"); top.pack(fill=X, pady=(0, 14))
        tk.Label(top, text=title, bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(side=LEFT)
        tree = ttk.Treeview(container, columns=columns, show="headings", style="Treeview")
        for c in columns: tree.heading(c, text=c); tree.column(c, anchor=CENTER)
        tree.pack(fill=BOTH, expand=True)
        for row in data: tree.insert("", "end", values=row)
        if show_toolbar:
            actions = tk.Frame(top, bg="#ffffff"); actions.pack(side=RIGHT)
            tb.Entry(actions, width=24).pack(side=LEFT, padx=(0,10))
            def add_item(): self._open_table_modal("Thêm Mới", title, columns, tree)
            def edit_item():
                sel=tree.selection()
                if not sel: return Messagebox.show_warning("Vui lòng click chọn một dòng để sửa!", "Cảnh báo")
                self._open_table_modal("Chỉnh Sửa", title, columns, tree, sel[0], tree.item(sel[0])["values"])
            def delete_item():
                sel=tree.selection()
                if not sel: return Messagebox.show_warning("Vui lòng click chọn một dòng để xóa!", "Cảnh báo")
                if Messagebox.yesno("Bạn có chắc chắn muốn xóa dòng dữ liệu này?", "Xác nhận xóa"):
                    tree.delete(sel[0]); self.show_toast("Thành công", "Đã xóa dữ liệu!", "success")
            tb.Button(actions, text="Thêm", bootstyle="success", command=add_item).pack(side=LEFT,padx=3)
            tb.Button(actions, text="Sửa", bootstyle="info", command=edit_item).pack(side=LEFT,padx=3)
            tb.Button(actions, text="Xóa", bootstyle="danger", command=delete_item).pack(side=LEFT,padx=3)

    def _open_table_modal(self, mode, title, columns, tree, item_id=None, item_values=None):
        modal = tb.Toplevel(self); modal.title(f"{mode} - {title}"); modal.geometry("460x460"); modal.position_center()
        tb.Label(modal, text=f"{mode.upper()} {title.upper()}", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=20)
        form = tk.Frame(modal); form.pack(fill=BOTH, expand=True, padx=24); form.columnconfigure(1, weight=1)
        entries = []; item_values = item_values or [""]*len(columns)
        for i, (col, val) in enumerate(zip(columns, item_values)):
            tb.Label(form, text=col + ":").grid(row=i, column=0, pady=9, sticky=E)
            var = tb.StringVar(value=str(val)); tb.Entry(form, textvariable=var).grid(row=i, column=1, padx=10, pady=9, sticky=EW); entries.append(var)
        def save():
            values = [v.get() for v in entries]
            if item_id: tree.item(item_id, values=values); self.show_toast("Thành công", "Đã cập nhật dữ liệu!", "success")
            else: tree.insert("", "end", values=values); self.show_toast("Thành công", "Đã thêm dữ liệu mới!", "success")
            modal.destroy()
        tb.Button(modal, text="Lưu Dữ Liệu", bootstyle="success", command=save).pack(pady=18, fill=X, padx=32, ipady=5)

    def _build_financials_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"])
        self.frames["Financials"] = f

        stats = tk.Frame(f, bg=self.colors["bg"])
        stats.pack(fill=X, pady=(0, 14))

        self.fin_stat_income = self.create_stat_card(
            stats, 0, "Tổng thu", "0 VNĐ", self.colors["green"], self.colors["soft_green"]
        )
        self.fin_stat_expense = self.create_stat_card(
            stats, 1, "Tổng chi", "0 VNĐ", self.colors["orange"], self.colors["soft_orange"]
        )
        self.fin_stat_profit = self.create_stat_card(
            stats, 2, "Lợi nhuận", "0 VNĐ", self.colors["blue"], self.colors["soft_blue"]
        )

        content = tk.Frame(f, bg=self.colors["bg"])
        content.pack(fill=BOTH, expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        left = self.make_card(content, padx=18, pady=16)
        left.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))

        right = self.make_card(content, padx=22, pady=14)
        right.grid(row=0, column=1, sticky=NSEW, padx=(10, 0))

        title_row = tk.Frame(left, bg="#ffffff")
        title_row.pack(fill=X, pady=(0, 10))
        tk.Label(
            title_row,
            text="Sổ Thu Chi Khách Sạn",
            bg="#ffffff",
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold")
        ).pack(side=LEFT)

        toolbar_search = tk.Frame(left, bg="#ffffff")
        toolbar_search.pack(fill=X, pady=(0, 8))
        self.fin_search_var = tk.StringVar()
        tb.Entry(toolbar_search, textvariable=self.fin_search_var, width=24).pack(side=LEFT, padx=(0, 8))
        tb.Button(toolbar_search, text="Tìm", bootstyle="outline-primary", command=self.search_financials, width=8).pack(side=LEFT)

        toolbar_action = tk.Frame(left, bg="#ffffff")
        toolbar_action.pack(fill=X, pady=(0, 12))
        tb.Button(toolbar_action, text="Thêm", bootstyle="success", command=lambda: self.open_financial_modal("add"), width=9).pack(side=LEFT, padx=(0, 6))
        tb.Button(toolbar_action, text="Sửa", bootstyle="info", command=lambda: self.open_financial_modal("edit"), width=9).pack(side=LEFT, padx=(0, 6))
        tb.Button(toolbar_action, text="Xóa", bootstyle="danger", command=self.delete_financial_item, width=9).pack(side=LEFT)

        cols = ("Mã GD", "Ngày", "Loại", "Nội dung", "Số tiền")
        self.tree_financial = ttk.Treeview(left, columns=cols, show="headings", style="Treeview")
        widths = [100, 160, 80, 250, 140]
        for c, w in zip(cols, widths):
            self.tree_financial.heading(c, text=c)
            self.tree_financial.column(c, width=w, anchor=CENTER)
        self.tree_financial.pack(fill=BOTH, expand=True)
        self.tree_financial.bind("<<TreeviewSelect>>", self.on_financial_select)

        tk.Label(right, text="Chi Tiết Giao Dịch", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor=W)
        tk.Label(right, text="Theo dõi dòng tiền thu / chi và liên kết với thanh toán phòng", bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 10)).pack(anchor=W, pady=(4, 12))

        self.fin_code_lbl = tk.Label(right, text="Mã giao dịch: ---", bg="#ffffff", fg="#0f172a", font=("Segoe UI", 11, "bold"))
        self.fin_code_lbl.pack(anchor=W, pady=3)
        self.fin_date_lbl = tk.Label(right, text="Ngày phát sinh: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.fin_date_lbl.pack(anchor=W, pady=3)
        self.fin_type_lbl = tk.Label(right, text="Loại: ---", bg="#ffffff", fg=self.colors["orange"], font=("Segoe UI", 11, "bold"))
        self.fin_type_lbl.pack(anchor=W, pady=3)
        self.fin_amount_lbl = tk.Label(right, text="Số tiền: ---", bg="#ffffff", fg=self.colors["green"], font=("Segoe UI", 11, "bold"))
        self.fin_amount_lbl.pack(anchor=W, pady=3)
        self.fin_source_lbl = tk.Label(right, text="Nguồn: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.fin_source_lbl.pack(anchor=W, pady=(3, 10))

        tk.Label(right, text="Nội dung", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(0, 6))
        self.fin_note_text = tk.Text(
            right,
            height=6,
            wrap="word",
            font=("Segoe UI", 10),
            relief=FLAT,
            bg="#f8fafc",
            fg="#334155",
            padx=12,
            pady=10,
        )
        self.fin_note_text.pack(fill=BOTH, expand=True)

        right_footer = tk.Frame(right, bg="#ffffff")
        right_footer.pack(fill=X, pady=(8, 0))
        right_footer.columnconfigure(0, weight=1)
        right_footer.columnconfigure(1, weight=1)
        right_footer.columnconfigure(2, weight=1)
        tb.Button(right_footer, text="Thêm", bootstyle="success", command=lambda: self.open_financial_modal("add")).grid(row=0, column=0, sticky=EW, padx=(0, 6), ipady=5)
        tb.Button(right_footer, text="Sửa", bootstyle="info", command=lambda: self.open_financial_modal("edit")).grid(row=0, column=1, sticky=EW, padx=6, ipady=5)
        tb.Button(right_footer, text="Xóa", bootstyle="danger", command=self.delete_financial_item).grid(row=0, column=2, sticky=EW, padx=(6, 0), ipady=5)

        self.refresh_financials()

    def refresh_financials(self, keyword=""):
        if not hasattr(self, "tree_financial"):
            return

        for item in self.tree_financial.get_children():
            self.tree_financial.delete(item)

        keyword = keyword.strip().lower()
        for idx, row in enumerate(self.financial_data):
            blob = f"{row['code']} {row['date']} {row['type']} {row['description']} {row['source']}".lower()
            if keyword and keyword not in blob:
                continue
            sign = "+" if row["type"] == "THU" else "-"
            self.tree_financial.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    row["code"],
                    row["date"],
                    row["type"],
                    row["description"],
                    f"{sign} {format_currency(row['amount'])}",
                ),
            )

        income, expense, profit = self.get_financial_totals()
        self.fin_stat_income.config(text=format_currency(income))
        self.fin_stat_expense.config(text=format_currency(expense))
        self.fin_stat_profit.config(text=format_currency(profit))

        self.fin_code_lbl.config(text="Mã giao dịch: ---")
        self.fin_date_lbl.config(text="Ngày phát sinh: ---")
        self.fin_type_lbl.config(text="Loại: ---", fg=self.colors["orange"])
        self.fin_amount_lbl.config(text="Số tiền: ---", fg=self.colors["green"])
        self.fin_source_lbl.config(text="Nguồn: ---")
        self._fill_text(self.fin_note_text, "Chọn một giao dịch ở bên trái để xem chi tiết.")

    def on_financial_select(self, event=None):
        sel = self.tree_financial.selection()
        if not sel:
            return
        idx = int(sel[0])
        item = self.financial_data[idx]
        sign = "+" if item["type"] == "THU" else "-"
        color = self.colors["green"] if item["type"] == "THU" else self.colors["orange"]

        self.fin_code_lbl.config(text=f"Mã giao dịch: {item['code']}")
        self.fin_date_lbl.config(text=f"Ngày phát sinh: {item['date']}")
        self.fin_type_lbl.config(text=f"Loại: {item['type']}", fg=color)
        self.fin_amount_lbl.config(text=f"Số tiền: {sign} {format_currency(item['amount'])}", fg=color)
        self.fin_source_lbl.config(text=f"Nguồn: {item['source']}")
        self._fill_text(self.fin_note_text, item["description"])

    def search_financials(self):
        self.refresh_financials(self.fin_search_var.get().strip())

    def open_financial_modal(self, mode="add"):
        edit_mode = mode == "edit"
        if edit_mode:
            sel = self.tree_financial.selection()
            if not sel:
                return Messagebox.show_warning(
                    "Vui lòng chọn một giao dịch để chỉnh sửa!",
                    "Chưa chọn dữ liệu"
                )
            idx = int(sel[0])
            data = self.financial_data[idx]
        else:
            idx = None
            data = {
                "code": self._next_financial_code(),
                "date": self._now_str(),
                "type": "THU",
                "description": "",
                "amount": 0,
                "source": "Nhập tay",
            }

        modal = tb.Toplevel(self)
        modal.title("Giao dịch tài chính")
        modal.geometry("660x740")
        modal.minsize(660, 740)
        modal.resizable(False, False)
        modal.position_center()

        tk.Label(
            modal,
            text="THÔNG TIN GIAO DỊCH",
            bg=modal.cget("bg"),
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold")
        ).pack(pady=(18, 12))

        form = tk.Frame(
            modal,
            bg="#ffffff",
            padx=20,
            pady=18,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        form.pack(fill=X, expand=False, padx=24, pady=(0, 10))
        form.columnconfigure(1, weight=1)

        code_var = tb.StringVar(value=str(data["code"]))
        date_var = tb.StringVar(value=str(data["date"]))
        type_var = tb.StringVar(value=str(data["type"]))
        amount_var = tb.StringVar(value=str(int(float(data["amount"]))))
        source_var = tb.StringVar(value=str(data["source"]))

        fields = [
            ("Mã giao dịch:", code_var),
            ("Ngày phát sinh:", date_var),
            ("Số tiền:", amount_var),
            ("Nguồn:", source_var),
        ]

        for i, (label, var) in enumerate(fields):
            tk.Label(
                form,
                text=label,
                bg="#ffffff",
                fg=self.colors["text"],
                font=("Segoe UI", 10)
            ).grid(row=i, column=0, sticky=E, padx=(0, 12), pady=8)

            tb.Entry(form, textvariable=var).grid(
                row=i, column=1, sticky=EW, pady=8
            )

        tk.Label(
            form,
            text="Loại:",
            bg="#ffffff",
            fg=self.colors["text"],
            font=("Segoe UI", 10)
        ).grid(row=4, column=0, sticky=E, padx=(0, 12), pady=8)

        ttk.Combobox(
            form,
            textvariable=type_var,
            values=["THU", "CHI"],
            state="readonly"
        ).grid(row=4, column=1, sticky=EW, pady=8)

        tk.Label(
            form,
            text="Nội dung:",
            bg="#ffffff",
            fg=self.colors["text"],
            font=("Segoe UI", 10)
        ).grid(row=5, column=0, sticky=NE, padx=(0, 12), pady=8)

        desc_text = tk.Text(
            form,
            height=4,
            font=("Segoe UI", 10),
            wrap="word"
        )
        desc_text.grid(row=5, column=1, sticky=EW, pady=8)
        desc_text.insert("1.0", data["description"])

        def save():
            try:
                amount = float(amount_var.get().strip())
            except Exception:
                return Messagebox.show_warning(
                    "Số tiền phải là số!",
                    "Dữ liệu không hợp lệ"
                )

            old_amount = float(data["amount"]) if edit_mode else 0
            old_type = data["type"] if edit_mode else None

            new_record = {
                "code": code_var.get().strip(),
                "date": date_var.get().strip(),
                "type": type_var.get().strip(),
                "description": desc_text.get("1.0", END).strip(),
                "amount": amount,
                "source": source_var.get().strip() or "Nhập tay",
            }

            if not new_record["code"] or not new_record["description"]:
                return Messagebox.show_warning(
                    "Vui lòng nhập đầy đủ mã giao dịch và nội dung!",
                    "Thiếu dữ liệu"
                )

            if edit_mode:
                if old_type == "THU":
                    self.total_revenue -= old_amount
                if new_record["type"] == "THU":
                    self.total_revenue += amount
                self.financial_data[idx] = new_record
                self.show_toast("Thành công", "Đã cập nhật giao dịch.", "success")
            else:
                if new_record["type"] == "THU":
                    self.total_revenue += amount
                self.financial_data.insert(0, new_record)
                self.show_toast("Thành công", "Đã thêm giao dịch tài chính.", "success")

            self._save_all_financials()
            modal.destroy()
            self.refresh_financials()
            self.refresh_dashboard()

        footer = tk.Frame(modal, bg=modal.cget("bg"))
        footer.pack(fill=X, padx=24, pady=(4, 18))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)

        tb.Button(
            footer,
            text="Lưu giao dịch",
            bootstyle="success",
            command=save
        ).grid(row=0, column=0, sticky=EW, padx=(0, 6), pady=2)

        tb.Button(
            footer,
            text="Đóng",
            bootstyle="secondary",
            command=modal.destroy
        ).grid(row=0, column=1, sticky=EW, padx=(6, 0), pady=2)

    def delete_financial_item(self):
        sel = self.tree_financial.selection()
        if not sel:
            return Messagebox.show_warning("Vui lòng chọn một giao dịch để xóa!", "Chưa chọn dữ liệu")
        idx = int(sel[0])
        item = self.financial_data[idx]
        if Messagebox.yesno("Bạn có chắc chắn muốn xóa giao dịch này?", "Xác nhận xóa"):
            if item["type"] == "THU":
                self.total_revenue -= float(item["amount"])
            del self.financial_data[idx]
            self._save_all_financials()
            self.show_toast("Thành công", "Đã xóa giao dịch.", "success")
            self.refresh_financials()
            self.refresh_dashboard()

    def _build_reviews_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"]); self.frames["Reviews"] = f
        self._create_modern_table(f, "Phản Hồi & Đánh Giá", ("Tên Khách Hàng", "Mục Tiêu", "Đánh Giá", "Nội Dung"), [("Anh Khang", "Dịch vụ", "⭐⭐⭐⭐⭐", "Rất tốt!")], show_toolbar=False)

    def _build_concierge_frame(self):
        f = tk.Frame(self.container, bg=self.colors["bg"])
        self.frames["Concierge"] = f

        stats = tk.Frame(f, bg=self.colors["bg"])
        stats.pack(fill=X, pady=(0, 14))
        self.sup_stat_total = self.create_stat_card(stats, 0, "Tổng yêu cầu", "0", self.colors["blue"], self.colors["soft_blue"])
        self.sup_stat_wait = self.create_stat_card(stats, 1, "Chờ xử lý", "0", self.colors["orange"], self.colors["soft_orange"])
        self.sup_stat_processing = self.create_stat_card(stats, 2, "Đang xử lý", "0", self.colors["green"], self.colors["soft_green"])
        self.sup_stat_done = self.create_stat_card(stats, 3, "Hoàn thành", "0", self.colors["purple"], self.colors["soft_purple"])

        content = tk.Frame(f, bg=self.colors["bg"])
        content.pack(fill=BOTH, expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        left = self.make_card(content, padx=18, pady=16)
        left.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))
        right = self.make_card(content, padx=22, pady=14)
        right.grid(row=0, column=1, sticky=NSEW, padx=(10, 0))

        title_row = tk.Frame(left, bg="#ffffff")
        title_row.pack(fill=X, pady=(0, 10))
        tk.Label(title_row, text="Trung Tâm Hỗ Trợ", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(side=LEFT)

        toolbar_search = tk.Frame(left, bg="#ffffff")
        toolbar_search.pack(fill=X, pady=(0, 8))
        self.support_search_var = tk.StringVar()
        tb.Entry(toolbar_search, textvariable=self.support_search_var, width=22).pack(side=LEFT, padx=(0, 8))
        tb.Button(toolbar_search, text="Tìm", bootstyle="outline-primary", command=self.search_supports, width=8).pack(side=LEFT)

        toolbar_action = tk.Frame(left, bg="#ffffff")
        toolbar_action.pack(fill=X, pady=(0, 12))
        for text, style, cmd, width in [
            ("Thêm", "success", lambda: self.open_support_modal("add"), 8),
            ("Sửa", "info", lambda: self.open_support_modal("edit"), 8),
            ("Xử lý", "warning", self.mark_support_processing, 8),
            ("Xong", "secondary", self.mark_support_done, 8),
            ("Xóa", "danger", self.delete_support_request, 8),
        ]:
            tb.Button(toolbar_action, text=text, bootstyle=style, command=cmd, width=width).pack(side=LEFT, padx=3)

        cols = ("Mã YC", "Khu vực", "Dịch vụ", "Ưu tiên", "Trạng thái")
        self.tree_support = ttk.Treeview(left, columns=cols, show="headings", style="Treeview")
        widths = [110, 130, 210, 100, 130]
        for c, w in zip(cols, widths):
            self.tree_support.heading(c, text=c)
            self.tree_support.column(c, width=w, anchor=CENTER)
        self.tree_support.pack(fill=BOTH, expand=True)
        self.tree_support.bind("<<TreeviewSelect>>", self.on_support_select)

        tk.Label(right, text="Chi Tiết Yêu Cầu", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 16, "bold")).pack(anchor=W)
        tk.Label(right, text="Theo dõi yêu cầu hỗ trợ của khách và xử lý nhanh theo trạng thái", bg="#ffffff", fg=self.colors["muted"], font=("Segoe UI", 10), wraplength=430, justify=LEFT).pack(anchor=W, pady=(4, 12))

        self.sup_id_lbl = tk.Label(right, text="Mã yêu cầu: ---", bg="#ffffff", fg="#0f172a", font=("Segoe UI", 11, "bold"))
        self.sup_id_lbl.pack(anchor=W, pady=3)
        self.sup_area_lbl = tk.Label(right, text="Khu vực: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.sup_area_lbl.pack(anchor=W, pady=3)
        self.sup_guest_lbl = tk.Label(right, text="Khách/Phòng: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.sup_guest_lbl.pack(anchor=W, pady=3)
        self.sup_service_lbl = tk.Label(right, text="Dịch vụ: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.sup_service_lbl.pack(anchor=W, pady=3)
        self.sup_staff_lbl = tk.Label(right, text="Phụ trách: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.sup_staff_lbl.pack(anchor=W, pady=3)
        self.sup_priority_lbl = tk.Label(right, text="Ưu tiên: ---", bg="#ffffff", fg=self.colors["orange"], font=("Segoe UI", 11, "bold"))
        self.sup_priority_lbl.pack(anchor=W, pady=3)
        self.sup_status_lbl = tk.Label(right, text="Trạng thái: ---", bg="#ffffff", fg=self.colors["green"], font=("Segoe UI", 11, "bold"))
        self.sup_status_lbl.pack(anchor=W, pady=3)
        self.sup_time_lbl = tk.Label(right, text="Thời gian: ---", bg="#ffffff", fg="#475569", font=("Segoe UI", 11))
        self.sup_time_lbl.pack(anchor=W, pady=(3, 10))

        tk.Label(right, text="Ghi chú", bg="#ffffff", fg=self.colors["text"], font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(0, 6))
        self.sup_note_text = tk.Text(right, height=6, wrap="word", font=("Segoe UI", 10), relief=FLAT, bg="#f8fafc", fg="#334155", padx=12, pady=10)
        self.sup_note_text.pack(fill=BOTH, expand=True)

        right_footer = tk.Frame(right, bg="#ffffff")
        right_footer.pack(fill=X, pady=(8, 0))
        right_footer.columnconfigure(0, weight=1)
        right_footer.columnconfigure(1, weight=1)
        right_footer.columnconfigure(2, weight=1)
        tb.Button(right_footer, text="Nhận xử lý", bootstyle="warning", command=self.mark_support_processing).grid(row=0, column=0, sticky=EW, padx=(0, 6), ipady=5)
        tb.Button(right_footer, text="Hoàn thành", bootstyle="success", command=self.mark_support_done).grid(row=0, column=1, sticky=EW, padx=6, ipady=5)
        tb.Button(right_footer, text="Xóa", bootstyle="danger", command=self.delete_support_request).grid(row=0, column=2, sticky=EW, padx=(6, 0), ipady=5)

        self.refresh_supports()

    def refresh_supports(self, keyword=""):
        if not hasattr(self, "tree_support"):
            return
        for item in self.tree_support.get_children():
            self.tree_support.delete(item)

        keyword = keyword.strip().lower()
        for idx, row in enumerate(self.support_data):
            blob = f"{row['request_id']} {row['area']} {row['service']} {row['status']} {row['guest']} {row['staff']} {row['priority']}".lower()
            if keyword and keyword not in blob:
                continue
            self.tree_support.insert(
                "",
                "end",
                iid=str(idx),
                values=(row["request_id"], row["area"], row["service"], row["priority"], row["status"]),
            )

        total_support = len(self.support_data)
        waiting = sum(1 for x in self.support_data if x["status"] == "Chờ xử lý")
        processing = sum(1 for x in self.support_data if x["status"] == "Đang xử lý")
        done = sum(1 for x in self.support_data if x["status"] == "Hoàn thành")
        self.sup_stat_total.config(text=str(total_support))
        self.sup_stat_wait.config(text=str(waiting))
        self.sup_stat_processing.config(text=str(processing))
        self.sup_stat_done.config(text=str(done))

        self.sup_id_lbl.config(text="Mã yêu cầu: ---")
        self.sup_area_lbl.config(text="Khu vực: ---")
        self.sup_guest_lbl.config(text="Khách/Phòng: ---")
        self.sup_service_lbl.config(text="Dịch vụ: ---")
        self.sup_staff_lbl.config(text="Phụ trách: ---")
        self.sup_priority_lbl.config(text="Ưu tiên: ---", fg=self.colors["orange"])
        self.sup_status_lbl.config(text="Trạng thái: ---", fg=self.colors["green"])
        self.sup_time_lbl.config(text="Thời gian: ---")
        self._fill_text(self.sup_note_text, "Chọn một yêu cầu ở bên trái để xem chi tiết.")

    def on_support_select(self, event=None):
        sel = self.tree_support.selection()
        if not sel:
            return
        idx = int(sel[0])
        item = self.support_data[idx]
        self.sup_id_lbl.config(text=f"Mã yêu cầu: {item['request_id']}")
        self.sup_area_lbl.config(text=f"Khu vực: {item['area']}")
        self.sup_guest_lbl.config(text=f"Khách/Phòng: {item['guest']}")
        self.sup_service_lbl.config(text=f"Dịch vụ: {item['service']}")
        self.sup_staff_lbl.config(text=f"Phụ trách: {item['staff']}")
        self.sup_priority_lbl.config(text=f"Ưu tiên: {item['priority']}", fg=self.colors["red"] if item["priority"] == "Cao" else self.colors["orange"])
        self.sup_status_lbl.config(text=f"Trạng thái: {item['status']}", fg=self.colors["green"] if item["status"] == "Hoàn thành" else self.colors["orange"])
        self.sup_time_lbl.config(text=f"Thời gian: {item['time']}")
        self._fill_text(self.sup_note_text, item["note"])

    def search_supports(self):
        self.refresh_supports(self.support_search_var.get().strip())

    def open_support_modal(self, mode="add"):
        edit_mode = mode == "edit"
        if edit_mode:
            sel = self.tree_support.selection()
            if not sel:
                return Messagebox.show_warning("Vui lòng chọn một yêu cầu để chỉnh sửa!", "Chưa chọn dữ liệu")
            idx = int(sel[0])
            data = self.support_data[idx]
        else:
            idx = None
            data = {
                "request_id": f"RQ-{100 + len(self.support_data) + 1}",
                "area": "",
                "service": "",
                "status": "Chờ xử lý",
                "guest": "",
                "priority": "Trung bình",
                "staff": "",
                "note": "",
                "time": self._now_str(),
            }

        modal = tb.Toplevel(self)
        modal.title("Yêu cầu hỗ trợ")
        modal.geometry("680x760")
        modal.minsize(680, 760)
        modal.resizable(False, False)
        modal.position_center()

        root = tk.Frame(modal, bg=modal.cget("bg"))
        root.pack(fill=BOTH, expand=True, padx=18, pady=14)
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

        tk.Label(
            root,
            text="THÔNG TIN YÊU CẦU HỖ TRỢ",
            bg=modal.cget("bg"),
            fg=self.colors["text"],
            font=(self.font_family, 15, "bold")
        ).grid(row=0, column=0, sticky=EW, pady=(0, 10))

        form = tk.Frame(
            root,
            bg="#ffffff",
            padx=18,
            pady=12,
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        form.grid(row=1, column=0, sticky=NSEW)
        form.columnconfigure(1, weight=1)

        req_var = tb.StringVar(value=data["request_id"])
        area_var = tb.StringVar(value=data["area"])
        service_var = tb.StringVar(value=data["service"])
        guest_var = tb.StringVar(value=data["guest"])
        staff_var = tb.StringVar(value=data["staff"])
        time_var = tb.StringVar(value=data["time"])
        priority_var = tb.StringVar(value=data["priority"])
        status_var = tb.StringVar(value=data["status"])

        fields = [
            ("Mã yêu cầu:", req_var),
            ("Khu vực:", area_var),
            ("Dịch vụ:", service_var),
            ("Khách/Phòng:", guest_var),
            ("Phụ trách:", staff_var),
            ("Thời gian:", time_var),
        ]
        for i, (label, var) in enumerate(fields):
            tk.Label(
                form,
                text=label,
                bg="#ffffff",
                fg=self.colors["text"],
                font=(self.font_family, 10)
            ).grid(row=i, column=0, sticky=E, padx=(0, 10), pady=5)
            tb.Entry(form, textvariable=var).grid(row=i, column=1, sticky=EW, pady=5)

        tk.Label(form, text="Ưu tiên:", bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 10)).grid(row=6, column=0, sticky=E, padx=(0, 10), pady=5)
        ttk.Combobox(form, textvariable=priority_var, values=["Thấp", "Trung bình", "Cao"], state="readonly").grid(row=6, column=1, sticky=EW, pady=5)

        tk.Label(form, text="Trạng thái:", bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 10)).grid(row=7, column=0, sticky=E, padx=(0, 10), pady=5)
        ttk.Combobox(form, textvariable=status_var, values=["Chờ xử lý", "Đang xử lý", "Hoàn thành"], state="readonly").grid(row=7, column=1, sticky=EW, pady=5)

        tk.Label(form, text="Ghi chú:", bg="#ffffff", fg=self.colors["text"], font=(self.font_family, 10)).grid(row=8, column=0, sticky=NE, padx=(0, 10), pady=5)
        note_text = tk.Text(form, height=3, font=(self.font_family, 10), wrap="word")
        note_text.grid(row=8, column=1, sticky=NSEW, pady=5)
        note_text.insert("1.0", data["note"])
        form.rowconfigure(8, weight=1)

        def save():
            new_item = {
                "request_id": req_var.get().strip(),
                "area": area_var.get().strip(),
                "service": service_var.get().strip(),
                "status": status_var.get().strip(),
                "guest": guest_var.get().strip(),
                "priority": priority_var.get().strip(),
                "staff": staff_var.get().strip(),
                "note": note_text.get("1.0", END).strip(),
                "time": time_var.get().strip(),
            }
            if not new_item["request_id"] or not new_item["area"] or not new_item["service"]:
                return Messagebox.show_warning("Vui lòng nhập đủ Mã yêu cầu, Khu vực và Dịch vụ!", "Thiếu dữ liệu")
            if edit_mode:
                self.support_data[idx] = new_item
                self.show_toast("Thành công", "Đã cập nhật yêu cầu hỗ trợ.", "success")
            else:
                self.support_data.insert(0, new_item)
                self.show_toast("Thành công", "Đã thêm yêu cầu hỗ trợ mới.", "success")
            self._save_all_supports()
            modal.destroy()
            self.refresh_supports()

        footer = tk.Frame(root, bg=modal.cget("bg"))
        footer.grid(row=2, column=0, sticky=EW, pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)

        tb.Button(footer, text="Lưu dữ liệu", bootstyle="success", command=save).grid(row=0, column=0, sticky=EW, padx=(0, 6), pady=2)
        tb.Button(footer, text="Đóng", bootstyle="secondary", command=modal.destroy).grid(row=0, column=1, sticky=EW, padx=(6, 0), pady=2)

    def delete_support_request(self):
        sel = self.tree_support.selection()
        if not sel:
            return Messagebox.show_warning("Vui lòng chọn một yêu cầu để xóa!", "Chưa chọn dữ liệu")
        idx = int(sel[0])
        if Messagebox.yesno("Bạn có chắc chắn muốn xóa yêu cầu này?", "Xác nhận xóa"):
            del self.support_data[idx]
            self._save_all_supports()
            self.show_toast("Thành công", "Đã xóa yêu cầu hỗ trợ.", "success")
            self.refresh_supports()

    def mark_support_processing(self):
        sel = self.tree_support.selection()
        if not sel:
            return Messagebox.show_warning("Vui lòng chọn một yêu cầu!", "Chưa chọn dữ liệu")
        idx = int(sel[0])
        self.support_data[idx]["status"] = "Đang xử lý"
        self._save_all_supports()
        self.show_toast("Cập nhật", "Yêu cầu đã được chuyển sang trạng thái Đang xử lý.", "info")
        self.refresh_supports()

    def mark_support_done(self):
        sel = self.tree_support.selection()
        if not sel:
            return Messagebox.show_warning("Vui lòng chọn một yêu cầu!", "Chưa chọn dữ liệu")
        idx = int(sel[0])
        self.support_data[idx]["status"] = "Hoàn thành"
        self._save_all_supports()
        self.show_toast("Cập nhật", "Yêu cầu đã được hoàn thành.", "success")
        self.refresh_supports()

    def show_notifications(self):
        Messagebox.show_info(
            "Bạn có 3 thông báo mới:\n\n"
            "1. Yêu cầu kiểm tra khu vực 101.\n"
            "2. Có đơn đặt phòng VIP mới.\n"
            "3. Kho báo sắp hết vật tư giấy A4.",
            "Trung tâm thông báo",
        )


if __name__ == "__main__":
    app = HotelManagementApp()
    app.mainloop()
