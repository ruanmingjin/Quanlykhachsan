import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Cấu hình font chữ cho biểu đồ để không bị lỗi tiếng Việt
plt.rcParams['font.family'] = 'Arial'

class ModernDashboard(tb.Window):
    def __init__(self):
        super().__init__(themename="lumen") 
        self.title("Phần Mềm Quản Lý Khách Sạn - Nhóm 19")
        self.geometry("1400x850")
        self.state('zoomed') # Mở toàn màn hình
        
        self._build_layout()

    def _build_layout(self):
        # --- SIDEBAR (CỘT BÊN TRÁI) ---
        sidebar = tb.Frame(self, bootstyle="secondary", width=250)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False) 

        # Logo
        tb.Label(sidebar, text="🏨 Nhóm 19", font=("Helvetica", 22, "bold"), bootstyle="inverse-secondary").pack(pady=30)

        # Các nút Menu Tiếng Việt
        menus = ["Tổng quan", "Đặt phòng", "Quản lý phòng", "Tin nhắn", "Buồng phòng", "Tài chính", "Cài đặt"]
        for menu in menus:
            style = "success" if menu == "Tổng quan" else "secondary"
            btn = tb.Button(sidebar, text=f"  {menu}", bootstyle=f"{style}-link", width=25)
            btn.pack(pady=5, padx=20, anchor=W)

        # --- MAIN CONTENT (BÊN PHẢI) ---
        main_content = tb.Frame(self, padding=20)
        main_content.pack(side=LEFT, fill=BOTH, expand=True)

        # 1. TOP HEADER
        header_frame = tb.Frame(main_content)
        header_frame.pack(fill=X, pady=(0, 20))
        tb.Label(header_frame, text="Tổng Quan Hệ Thống", font=("Arial", 24, "bold")).pack(side=LEFT)
        tb.Label(header_frame, text="👤 Quản trị viên: Admin", font=("Arial", 12)).pack(side=RIGHT)

        # 2. CARDS FRAME (4 thẻ thông số)
        cards_frame = tb.Frame(main_content)
        cards_frame.pack(fill=X, pady=10)
        
        self._create_card(cards_frame, "Lượt Đặt Mới", "840", "success", 0)
        self._create_card(cards_frame, "Đang Lưu Trú", "231", "info", 1)
        self._create_card(cards_frame, "Đã Trả Phòng", "124", "danger", 2)
        self._create_card(cards_frame, "Tổng Doanh Thu", "123.980.000 đ", "warning", 3)

        # 3. CHARTS FRAME (Biểu đồ)
        charts_frame = tb.Frame(main_content)
        charts_frame.pack(fill=BOTH, expand=True, pady=10)
        self._build_charts(charts_frame)

        # 4. DATA TABLE (Bảng dữ liệu)
        table_frame = tb.Frame(main_content)
        table_frame.pack(fill=BOTH, expand=True, pady=10)
        tb.Label(table_frame, text="Danh Sách Đặt Phòng Gần Đây", font=("Arial", 16, "bold")).pack(anchor=W, pady=10)
        self._build_table(table_frame)

    def _create_card(self, parent, title, value, style, col):
        card = tb.Frame(parent, bootstyle=style, padding=20)
        card.grid(row=0, column=col, padx=10, sticky=EW)
        parent.columnconfigure(col, weight=1)
        
        tb.Label(card, text=title, font=("Arial", 12), bootstyle=f"inverse-{style}").pack(anchor=W)
        tb.Label(card, text=value, font=("Arial", 24, "bold"), bootstyle=f"inverse-{style}").pack(anchor=W, pady=(10, 0))

    def _build_charts(self, parent):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3), gridspec_kw={'width_ratios': [2, 1]})
        fig.patch.set_facecolor('#f8f9fa') 

        # Biểu đồ Đường (Doanh thu)
        thang = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5']
        doanh_thu = [100, 250, 200, 315, 280]
        ax1.plot(thang, doanh_thu, color='#28a745', marker='o')
        ax1.fill_between(thang, doanh_thu, color='#28a745', alpha=0.1)
        ax1.set_title("Biểu đồ Doanh Thu (Triệu VNĐ)", loc='left', fontsize=12, fontweight='bold')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)

        # Biểu đồ Tròn (Nguồn khách đặt phòng)
        sizes = [61, 12, 11, 9, 7]
        labels = ['Trực tiếp', 'Booking.com', 'Agoda', 'Airbnb', 'Nguồn khác']
        colors = ['#c8e6c9', '#a5d6a7', '#81c784', '#66bb6a', '#4caf50']
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90, wedgeprops=dict(width=0.4))
        ax2.set_title("Nền Tảng Đặt Phòng", loc='left', fontsize=12, fontweight='bold')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def _build_table(self, parent):
        cols = ("Mã Giao Dịch", "Tên Khách Hàng", "Loại Phòng", "Số Phòng", "Thời Gian", "Trạng Thái")
        tree = tb.Treeview(parent, columns=cols, show="headings", bootstyle="success")
        
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor=CENTER)
        
        tree.pack(fill=BOTH, expand=True)

        # Dữ liệu giả tiếng Việt
        data = [
            ("HD-00108", "Nguyễn Minh Tiến", "Cao cấp (Deluxe)", "Phòng 101", "3 đêm", "Đang lưu trú"),
            ("HD-00109", "Trần Thu Hà", "Tiêu chuẩn (Standard)", "Phòng 202", "2 đêm", "Đang lưu trú"),
            ("HD-00110", "Lê Gia Huy", "Thương gia (Suite)", "Phòng 303", "5 đêm", "Chờ nhận phòng"),
        ]
        for row in data:
            tree.insert("", "end", values=row)

if __name__ == "__main__":
    app = ModernDashboard()
    app.mainloop()