from datetime import date, datetime, timedelta
import sqlite3
import openai
import pandas as pd
import streamlit as st

# =========================================================
# 1. CẤU HÌNH TRANG & BIẾN HẰNG SỐ
# =========================================================
st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn Chuẩn Doanh nghiệp",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "hotel_enterprise.db"

ROOM_TYPES = ["Đơn", "Đôi", "VIP", "Gia đình", "Suite Deluxe"]
ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bảo trì", "Đã dọn dẹp"]
MAINTENANCE_STATUSES = ["Mới", "Đang xử lý", "Hoàn thành", "Hủy"]
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
ROLES = ["Lễ tân", "Buồng phòng", "Bảo trì", "Kế toán", "Quản lý", "Quản trị viên"]
SERVICE_CATEGORIES = ["Ăn uống / F&B", "Giặt ủi", "Minibar", "Dịch vụ khác"]


# =========================================================
# 2. KHỞI TẠO CƠ SỞ DỮ LIỆU TOÀN DIỆN (SQLITE)
# =========================================================
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Nhân viên
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        phone TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP
    )
    """)

    # Phòng
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        room_type TEXT NOT NULL,
        price_per_night REAL NOT NULL,
        status TEXT DEFAULT 'Trống',
        floor INTEGER DEFAULT 1
    )
    """)

    # Khách hàng
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        id_card TEXT UNIQUE NOT NULL,
        phone TEXT,
        email TEXT,
        note TEXT,
        created_at TIMESTAMP
    )
    """)

    # Đặt phòng & Lưu trú (Booking / Check-in)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        customer_id INTEGER,
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
        actual_check_in TIMESTAMP,
        actual_check_out TIMESTAMP,
        status TEXT DEFAULT 'Đã đặt', -- 'Đã đặt', 'Đang ở', 'Đã trả phòng', 'Đã hủy'
        deposit REAL DEFAULT 0,
        total_room_price REAL DEFAULT 0,
        note TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (room_id) REFERENCES rooms(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # Dịch vụ phát sinh (Minibar, F&B, Laundry...)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    )
    """)

    # Hóa đơn dịch vụ của phòng đang ở
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        service_id INTEGER,
        quantity INTEGER DEFAULT 1,
        total_price REAL NOT NULL,
        created_at TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """)

    # Thanh toán & Hóa đơn tài chính
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        room_amount REAL,
        service_amount REAL,
        discount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        final_amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'Tiền mặt',
        paid_at TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    )
    """)

    # Bảo trì / Sự cố
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL,
        status TEXT DEFAULT 'Mới',
        assigned_to TEXT,
        created_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    )
    """)

    # Chat nội bộ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        display_name TEXT,
        message TEXT,
        created_at TIMESTAMP
    )
    """)

    # Nhật ký hệ thống
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        created_at TIMESTAMP
    )
    """)

    # Dữ liệu mẫu ban đầu
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
        INSERT INTO employees (full_name, username, password, role, phone, active, created_at)
        VALUES ('Quản trị viên', 'admin', 'admin123', 'Quản trị viên', '0901234567', 1, ?)
        """,
            (datetime.now(),),
        )

        # Dữ liệu phòng mẫu
        rooms_data = [
            ("101", "Đơn", 500000, "Trống", 1),
            ("102", "Đơn", 500000, "Trống", 1),
            ("201", "Đôi", 800000, "Trống", 2),
            ("202", "Đôi", 800000, "Trống", 2),
            ("301", "VIP", 1500000, "Trống", 3),
            ("302", "Gia đình", 1200000, "Trống", 3),
            ("401", "Suite Deluxe", 2500000, "Trống", 4),
        ]
        cursor.executemany(
            """
        INSERT INTO rooms (room_number, room_type, price_per_night, status, floor)
        VALUES (?, ?, ?, ?, ?)
        """,
            rooms_data,
        )

        # Dữ liệu dịch vụ mẫu
        services_data = [
            ("Nước suối Aquafina", "Minibar", 15000),
            ("Bia Heineken", "Minibar", 35000),
            ("Snack khoai tây", "Minibar", 25000),
            ("Buffet Sáng", "Ăn uống / F&B", 100000),
            ("Giặt ủi áo sơ mi", "Giặt ủi", 40000),
            ("Thuê xe máy / ngày", "Dịch vụ khác", 150000),
        ]
        cursor.executemany(
            """
        INSERT INTO services (name, category, price)
        VALUES (?, ?, ?)
        """,
            services_data,
        )

    conn.commit()
    conn.close()


def execute_sql(query, params=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def read_df(query, params=()):
    conn = get_db()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def log_action(username, action):
    execute_sql(
        "INSERT INTO audit_logs (username, action, created_at) VALUES (?, ?, ?)",
        (username, action, datetime.now()),
    )


def money(val):
    if pd.isna(val):
        return "0 VNĐ"
    return f"{val:,.0f} VNĐ"


init_db()


# =========================================================
# 3. MÀN HÌNH ĐĂNG NHẬP
# =========================================================
if "user" not in st.session_state:
    st.session_state["user"] = None

if "ai_messages" not in st.session_state:
    st.session_state["ai_messages"] = []


def login_screen():
    st.markdown(
        "<h2 style='text-align: center; color: #1f77b4;'>🏨 HỆ THỐNG QUẢN LÝ KHÁCH SẠN ENTERPRISE</h2>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔑 Đăng nhập hệ thống")
            username = st.text_input("Tên tài khoản", key="login_username_input")
            password = st.text_input(
                "Mật khẩu", type="password", key="login_password_input"
            )
            submit = st.form_submit_button(
                "Đăng nhập", use_container_width=True
            )

            if submit:
                res = read_df(
                    "SELECT * FROM employees WHERE username=:u AND password=:p AND active=1",
                    {"u": username, "p": password},
                )
                if not res.empty:
                    user_info = res.iloc[0].to_dict()
                    st.session_state["user"] = user_info
                    log_action(user_info["username"], "Đăng nhập thành công")
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("❌ Tên tài khoản hoặc mật khẩu không chính xác!")


def role_allowed(required_roles):
    user = st.session_state.get("user")
    if not user:
        return False
    if user["role"] == "Quản trị viên":
        return True
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    return user["role"] in required_roles


# =========================================================
# 4. CHƯƠNG TRÌNH CHÍNH (MAIN APP)
# =========================================================
def main():
    if not st.session_state["user"]:
        login_screen()
        return

    user = st.session_state["user"]

    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {user['full_name']}")
    st.sidebar.caption(f"Chức vụ: **{user['role']}**")

    page_options = [
        "🏨 Sơ đồ & Trạng thái phòng",
        "📝 Quản lý Đặt & Nhận phòng",
        "🛍️ Dịch vụ & Hóa đơn phòng",
        "💳 Thanh toán & Check-out",
        "👥 Quản lý Khách hàng (CRM)",
        "🔧 Sự cố & Bảo trì",
        "📊 Báo cáo Doanh thu & Thống kê",
        "💬 Chatbox Nội bộ",
        "🌐 Trợ lý AI OpenRouter",
        "👨‍💼 Phân quyền Nhân viên",
    ]

    page = st.sidebar.radio(
        "Điều hướng nghiệp vụ", page_options, key="main_navigation_radio"
    )

    if st.sidebar.button(
        "🚪 Đăng xuất", use_container_width=True, key="btn_logout_sidebar"
    ):
        log_action(user["username"], "Đăng xuất")
        st.session_state["user"] = None
        st.rerun()

    st.sidebar.divider()

    # --- 1. SƠ ĐỒ & TRẠNG THÁI PHÒNG ---
    if page == "🏨 Sơ đồ & Trạng thái phòng":
        st.title("🏨 Sơ đồ phòng trực quan theo thời gian thực")

        rooms_df = read_df(
            "SELECT id, room_number AS `Số phòng`, room_type AS `Loại phòng`, price_per_night AS `Giá/Đêm`, status AS `Trạng thái`, floor AS `Tầng` FROM rooms ORDER BY floor, room_number"
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tổng số phòng", len(rooms_df))
        c2.metric(
            "Trống", len(rooms_df[rooms_df["Trạng thái"] == "Trống"])
        )
        c3.metric(
            "Đang ở", len(rooms_df[rooms_df["Trạng thái"] == "Đang ở"])
        )
        c4.metric(
            "Đã đặt", len(rooms_df[rooms_df["Trạng thái"] == "Đã đặt"])
        )
        c5.metric(
            "Bảo trì", len(rooms_df[rooms_df["Trạng thái"] == "Bảo trì"])
        )

        st.divider()

        status_colors = {
            "Trống": "#28a745",
            "Đang ở": "#dc3545",
            "Đã đặt": "#ffc107",
            "Bảo trì": "#6c757d",
            "Đã dọn dẹp": "#17a2b8",
        }

        floors = sorted(rooms_df["Tầng"].unique())
        for f in floors:
            st.markdown(f"### 🏢 Tầng {f}")
            f_rooms = rooms_df[rooms_df["Tầng"] == f]
            cols = st.columns(4)
            for idx, row in f_rooms.reset_index().iterrows():
                col = cols[idx % 4]
                bg_color = status_colors.get(row["Trạng thái"], "#ffffff")
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 12px;
                            margin-bottom: 15px;
                            background-color: {bg_color}15;
                            border-left: 6px solid {bg_color};
                        ">
                            <h4 style="margin:0;">Phòng {row['Số phòng']}</h4>
                            <p style="margin:2px 0;"><b>Loại:</b> {row['Loại phòng']}</p>
                            <p style="margin:2px 0;"><b>Giá:</b> {money(row['Giá/Đêm'])}</p>
                            <span style="
                                background-color: {bg_color};
                                color: white;
                                padding: 2px 8px;
                                border-radius: 4px;
                                font-size: 12px;
                            ">{row['Trạng thái']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with st.expander("📄 Xem bảng chi tiết danh sách phòng"):
            st.dataframe(rooms_df, use_container_width=True, hide_index=True)

    # --- 2. QUẢN LÝ ĐẶT & NHẬN PHÒNG ---
    elif page == "📝 Quản lý Đặt & Nhận phòng":
        st.title("📝 Quản lý Đặt phòng & Check-in / Check-out")

        tab_book, tab_active_bookings = st.tabs(
            ["➕ Tạo Đặt phòng / Nhận phòng", "📋 Danh sách Phiếu Đặt/Thuê"]
        )

        rooms_free = read_df(
            "SELECT id, room_number, room_type, price_per_night FROM rooms WHERE status IN ('Trống', 'Đã dọn dẹp')"
        )
        customers_df = read_df("SELECT id, full_name, id_card, phone FROM customers")

        with tab_book:
            with st.form("booking_form"):
                st.subheader("Thông tin Khách hàng")
                existing_cust = st.selectbox(
                    "Chọn khách hàng cũ (hoặc thêm mới bên tab Khách hàng)",
                    ["-- Chọn khách hàng --"]
                    + [
                        f"{c['full_name']} - CCCD: {c['id_card']}"
                        for _, c in customers_df.iterrows()
                    ],
                )

                st.subheader("Thông tin Đặt phòng")
                selected_room_str = st.selectbox(
                    "Chọn phòng trống",
                    [
                        f"Phòng {r['room_number']} ({r['room_type']} - {money(r['price_per_night'])}/đêm)"
                        for _, r in rooms_free.iterrows()
                    ],
                )

                c1, c2 = st.columns(2)
                with c1:
                    check_in = st.date_input("Ngày nhận phòng", date.today())
                with c2:
                    check_out = st.date_input(
                        "Ngày trả phòng dự kiến", date.today() + timedelta(days=1)
                    )

                deposit = st.number_input(
                    "Tiền cọc trước (VNĐ)", min_value=0.0, step=100000.0, value=0.0
                )
                action_type = st.radio(
                    "Loại thao tác",
                    ["Đặt phòng trước (Booking)", "Nhận phòng ngay (Check-in)"],
                    horizontal=True,
                )
                note = st.text_area("Ghi chú yêu cầu đặc biệt")

                submit_booking = st.form_submit_button(
                    "💾 Xác nhận tạo phiếu", use_container_width=True
                )

                if submit_booking:
                    if existing_cust == "-- Chọn khách hàng --":
                        st.error("Vui lòng chọn khách hàng hợp lệ.")
                    elif not rooms_free.empty:
                        cust_id = customers_df.iloc[
                            [
                                f"{c['full_name']} - CCCD: {c['id_card']}"
                                for _, c in customers_df.iterrows()
                            ].index(existing_cust)
                        ]["id"]
                        room_id = rooms_free.iloc[
                            [
                                f"Phòng {r['room_number']} ({r['room_type']} - {money(r['price_per_night'])}/đêm)"
                                for _, r in rooms_free.iterrows()
                            ].index(selected_room_str)
                        ]["id"]
                        price_per_night = rooms_free.iloc[
                            [
                                f"Phòng {r['room_number']} ({r['room_type']} - {money(r['price_per_night'])}/đêm)"
                                for _, r in rooms_free.iterrows()
                            ].index(selected_room_str)
                        ]["price_per_night"]

                        # Tính số đêm
                        nights = (check_out - check_in).days
                        if nights <= 0:
                            nights = 1

                        total_room_price = nights * price_per_night
                        status = (
                            "Đang ở"
                            if action_type == "Nhận phòng ngay (Check-in)"
                            else "Đã đặt"
                        )
                        room_status_update = (
                            "Đang ở"
                            if action_type == "Nhận phòng ngay (Check-in)"
                            else "Đã đặt"
                        )
                        actual_in = datetime.now() if status == "Đang ở" else None

                        execute_sql(
                            """
                            INSERT INTO bookings (room_id, customer_id, check_in_date, check_out_date, actual_check_in, status, deposit, total_room_price, note, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                room_id,
                                cust_id,
                                check_in,
                                check_out,
                                actual_in,
                                status,
                                deposit,
                                total_room_price,
                                note,
                                datetime.now(),
                            ),
                        )

                        execute_sql(
                            "UPDATE rooms SET status=? WHERE id=?",
                            (room_status_update, room_id),
                        )
                        log_action(
                            user["username"],
                            f"Tạo phiếu {status} cho phòng ID {room_id}",
                        )
                        st.success("✅ Tạo phiếu thành công!")
                        st.rerun()
                    else:
                        st.error("Không có phòng trống nào khả dụng.")

        with tab_active_bookings:
            bookings_df = read_df(
                """
                SELECT 
                    b.id AS `Mã Phiếu`,
                    r.room_number AS `Số Phòng`,
                    c.full_name AS `Khách Hàng`,
                    c.phone AS `Số Điện Thoại`,
                    b.check_in_date AS `Nhận (DK)`,
                    b.check_out_date AS `Trả (DK)`,
                    b.status AS `Trạng thái`,
                    b.deposit AS `Tiền Cọc`,
                    b.total_room_price AS `Tiền Phòng`
                FROM bookings b
                JOIN rooms r ON b.room_id = r.id
                JOIN customers c ON b.customer_id = c.id
                ORDER BY b.id DESC
                """
            )
            st.dataframe(bookings_df, use_container_width=True, hide_index=True)

    # --- 3. DỊCH VỤ & HÓA ĐƠN PHÒNG ---
    elif page == "🛍️ Dịch vụ & Hóa đơn phòng":
        st.title("🛍️ Gọi dịch vụ phát sinh (Minibar, F&B, Giặt ủi)")

        active_stays = read_df(
            """
            SELECT b.id AS booking_id, r.room_number, c.full_name 
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN customers c ON b.customer_id = c.id
            WHERE b.status = 'Đang ở'
            """
        )

        if active_stays.empty:
            st.info("Hiện không có phòng nào đang có khách lưu trú (Đang ở).")
        else:
            services_list = read_df("SELECT id, name, category, price FROM services")

            with st.form("service_order_form"):
                selected_stay = st.selectbox(
                    "Chọn phòng đang ở",
                    [
                        f"Phòng {s['room_number']} - Khách: {s['full_name']}"
                        for _, s in active_stays.iterrows()
                    ],
                )
                selected_serv = st.selectbox(
                    "Chọn dịch vụ sử dụng",
                    [
                        f"{sv['name']} ({sv['category']}) - {money(sv['price'])}"
                        for _, sv in services_list.iterrows()
                    ],
                )
                quantity = st.number_input("Số lượng", min_value=1, value=1)

                submit_serv = st.form_submit_button(
                    "➕ Thêm dịch vụ vào phòng", use_container_width=True
                )

                if submit_serv:
                    b_id = active_stays.iloc[
                        [
                            f"Phòng {s['room_number']} - Khách: {s['full_name']}"
                            for _, s in active_stays.iterrows()
                        ].index(selected_stay)
                    ]["booking_id"]
                    serv_id = services_list.iloc[
                        [
                            f"{sv['name']} ({sv['category']}) - {money(sv['price'])}"
                            for _, sv in services_list.iterrows()
                        ].index(selected_serv)
                    ]["id"]
                    unit_price = services_list.iloc[
                        [
                            f"{sv['name']} ({sv['category']}) - {money(sv['price'])}"
                            for _, sv in services_list.iterrows()
                        ].index(selected_serv)
                    ]["price"]

                    total_price = unit_price * quantity
                    execute_sql(
                        """
                        INSERT INTO booking_services (booking_id, service_id, quantity, total_price, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (b_id, serv_id, quantity, total_price, datetime.now()),
                    )
                    st.success("✅ Đã thêm dịch vụ thành công vào hóa đơn phòng!")
                    st.rerun()

            st.divider()
            st.subheader("📋 Bảng kê dịch vụ phát sinh hiện tại")
            serv_usage_df = read_df(
                """
                SELECT 
                    r.room_number AS `Phòng`,
                    s.name AS `Tên dịch vụ`,
                    bs.quantity AS `Số lượng`,
                    bs.total_price AS `Thành tiền`,
                    bs.created_at AS `Thời gian gọi`
                FROM booking_services bs
                JOIN bookings b ON bs.booking_id = b.id
                JOIN rooms r ON b.room_id = r.id
                JOIN services s ON bs.service_id = s.id
                WHERE b.status = 'Đang ở'
                ORDER BY bs.id DESC
                """
            )
            st.dataframe(serv_usage_df, use_container_width=True, hide_index=True)

    # --- 4. THANH TOÁN & CHECK-OUT ---
    elif page == "💳 Thanh toán & Check-out":
        st.title("💳 Thanh toán hóa đơn & Trả phòng (Check-out)")

        active_checkouts = read_df(
            """
            SELECT b.id AS booking_id, r.room_number, c.full_name, b.total_room_price, b.deposit, r.id AS room_id
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN customers c ON b.customer_id = c.id
            WHERE b.status = 'Đang ở'
            """
        )

        if active_checkouts.empty:
            st.info("Không có phòng nào đang ở để thực hiện thanh toán.")
        else:
            selected_co = st.selectbox(
                "Chọn phòng cần thanh toán",
                [
                    f"Phòng {ac['room_number']} - Khách: {ac['full_name']}"
                    for _, ac in active_checkouts.iterrows()
                ],
            )

            ac_info = active_checkouts.iloc[
                [
                    f"Phòng {ac['room_number']} - Khách: {ac['full_name']}"
                    for _, ac in active_checkouts.iterrows()
                ].index(selected_co)
            ]

            b_id = ac_info["booking_id"]
            room_id = ac_info["room_id"]
            room_price = ac_info["total_room_price"]
            deposit = ac_info["deposit"]

            # Tính tổng tiền dịch vụ
            serv_sum_df = read_df(
                "SELECT SUM(total_price) AS total_serv FROM booking_services WHERE booking_id=?",
                (b_id,),
            )
            total_serv = (
                serv_sum_df.iloc[0]["total_serv"]
                if not serv_sum_df.empty and pd.notna(serv_sum_df.iloc[0]["total_serv"])
                else 0.0
            )

            st.markdown("### 🧾 Chi tiết hóa đơn tạm tính")
            st.write(f"- **Tiền phòng:** {money(room_price)}")
            st.write(f"- **Tiền dịch vụ phát sinh:** {money(total_serv)}")
            st.write(f"- **Đã cọc trước:** -{money(deposit)}")

            sub_total = room_price + total_serv - deposit
            discount = st.number_input(
                "Giảm giá thêm (VNĐ)", min_value=0.0, step=50000.0, value=0.0
            )
            tax = st.number_input(
                "Thuế VAT (VNĐ / Hoặc phí phụ thu)",
                min_value=0.0,
                step=50000.0,
                value=0.0,
            )

            final_amount = sub_total - discount + tax
            st.markdown(f"### 💰 **TỔNG TIỀN THANH TOÁN: {money(final_amount)}**")

            pay_method = st.selectbox(
                "Hình thức thanh toán",
                ["Tiền mặt", "Chuyển khoản QR", "Thẻ tín dụng / Thẻ ngân hàng"],
            )

            if st.button(
                "✅ Xác nhận thanh toán & Check-out", use_container_width=True
            ):
                # Lưu bảng payments
                execute_sql(
                    """
                    INSERT INTO payments (booking_id, room_amount, service_amount, discount, tax, final_amount, payment_method, paid_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        b_id,
                        room_price,
                        total_serv,
                        discount,
                        tax,
                        final_amount,
                        pay_method,
                        datetime.now(),
                    ),
                )

                # Cập nhật trạng thái booking thành 'Đã trả phòng'
                execute_sql(
                    "UPDATE bookings SET status='Đã trả phòng', actual_check_out=? WHERE id=?",
                    (datetime.now(), b_id),
                )

                # Cập nhật phòng sang trạng thái 'Đã dọn dẹp' (chờ housekeeping)
                execute_sql(
                    "UPDATE rooms SET status='Đã dọn dẹp' WHERE id=?", (room_id,)
                )

                log_action(
                    user["username"],
                    f"Thanh toán và Check-out phòng ID {room_id} số tiền {final_amount}",
                )
                st.success(
                    "🎉 Thanh toán thành công! Phòng đã chuyển sang trạng thái chờ dọn dẹp."
                )
                st.rerun()

    # --- 5. QUẢN LÝ KHÁCH HÀNG (CRM) ---
    elif page == "👥 Quản lý Khách hàng (CRM)":
        st.title("👥 Quản lý thông tin khách hàng")
        tab_list_cust, tab_add_cust = st.tabs(
            ["📋 Danh sách khách hàng", "➕ Thêm khách hàng mới"]
        )

        with tab_list_cust:
            cust_df = read_df(
                "SELECT id AS `ID`, full_name AS `Họ và tên`, id_card AS `CCCD / Hộ chiếu`, phone AS `Số điện thoại`, email AS `Email`, note AS `Ghi chú`, created_at AS `Ngày tạo` FROM customers ORDER BY id DESC"
            )
            st.dataframe(cust_df, use_container_width=True, hide_index=True)

        with tab_add_cust:
            with st.form("add_customer_form"):
                c_name = st.text_input("Họ và tên khách hàng *")
                c_id_card = st.text_input("Số CCCD / Hộ chiếu *")
                c_phone = st.text_input("Số điện thoại")
                c_email = st.text_input("Email")
                c_note = st.text_area("Ghi chú khách hàng (VIP, lưu ý đặc biệt...)")
                submit_c = st.form_submit_button(
                    "💾 Lưu khách hàng", use_container_width=True
                )

                if submit_c:
                    if not c_name or not c_id_card:
                        st.error("Vui lòng điền họ tên và CCCD.")
                    else:
                        try:
                            execute_sql(
                                """
                                INSERT INTO customers (full_name, id_card, phone, email, note, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    c_name.strip(),
                                    c_id_card.strip(),
                                    c_phone,
                                    c_email,
                                    c_note,
                                    datetime.now(),
                                ),
                            )
                            st.success("✅ Thêm khách hàng thành công!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(
                                "❌ Số CCCD/Hộ chiếu này đã tồn tại trong hệ thống!"
                            )

    # --- 6. SỰ CỐ & BẢO TRÌ ---
    elif page == "🔧 Sự cố & Bảo trì":
        st.title("🔧 Quản lý sự cố & Kỹ thuật bảo trì")
        tab_report, tab_maint_list = st.tabs(
            ["🚨 Báo cáo sự cố mới", "📋 Danh sách bảo trì"]
        )

        rooms_df = read_df("SELECT id, room_number FROM rooms")
        room_map = {"Khu vực chung / Khác": None}
        for _, r in rooms_df.iterrows():
            room_map[f"Phòng {r['room_number']}"] = r["id"]

        with tab_report:
            with st.form("maint_form"):
                selected_loc = st.selectbox(
                    "Vị trí sự cố", list(room_map.keys())
                )
                title = st.text_input("Tiêu đề sự cố *")
                description = st.text_area("Mô tả chi tiết hư hỏng")
                priority = st.selectbox(
                    "Mức độ ưu tiên", PRIORITIES, index=1
                )
                assigned_to = st.text_input(
                    "Nhân viên kỹ thuật phụ trách", "Chưa phân công"
                )
                submit_maint = st.form_submit_button("Gửi báo cáo sự cố")

            if submit_maint:
                if not title.strip():
                    st.error("Vui lòng nhập tiêu đề sự cố.")
                else:
                    room_id = room_map[selected_loc]
                    execute_sql(
                        """
                        INSERT INTO maintenance (room_id, title, description, priority, status, assigned_to, created_at)
                        VALUES (?, ?, ?, ?, 'Mới', ?, ?)
                        """,
                        (
                            room_id,
                            title.strip(),
                            description,
                            priority,
                            assigned_to,
                            datetime.now(),
                        ),
                    )
                    if room_id:
                        execute_sql(
                            "UPDATE rooms SET status='Bảo trì' WHERE id=?",
                            (room_id,),
                        )
                    st.success("✅ Đã gửi báo cáo bảo trì!")
                    st.rerun()

        with tab_maint_list:
            maint_df = read_df(
                """
                SELECT 
                    m.id AS `ID`,
                    COALESCE('P.' || r.room_number, 'Khu vực chung') AS `Vị trí`,
                    m.title AS `Sự cố`,
                    m.priority AS `Ưu tiên`,
                    m.status AS `Trạng thái`,
                    m.assigned_to AS `Xử lý bởi`,
                    m.created_at AS `Thời gian tạo`
                FROM maintenance m
                LEFT JOIN rooms r ON r.id = m.room_id
                ORDER BY m.id DESC
                """
            )
            st.dataframe(maint_df, use_container_width=True, hide_index=True)

    # --- 7. BÁO CÁO DOANH THU & THỐNG KÊ ---
    elif page == "📊 Báo cáo Doanh thu & Thống kê":
        st.title("📊 Báo cáo Doanh thu tài chính")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input(
                "Từ ngày", date.today() - timedelta(days=30)
            )
        with c2:
            end_date = st.date_input("Đến ngày", date.today())

        df_rev = read_df(
            """
            SELECT 
                DATE(paid_at) AS `Ngày`,
                SUM(final_amount) AS `Doanh thu`,
                COUNT(id) AS `Số lượng hóa đơn`
            FROM payments
            WHERE DATE(paid_at) BETWEEN ? AND ?
            GROUP BY DATE(paid_at)
            ORDER BY Ngày ASC
            """,
            (start_date, end_date),
        )

        if df_rev.empty:
            st.info("Chưa có dữ liệu doanh thu thanh toán trong khoảng thời gian này.")
        else:
            total_rev = df_rev["Doanh thu"].sum()
            st.metric("💸 Tổng doanh thu thực tế", money(total_rev))
            st.line_chart(df_rev.set_index("Ngày")["Doanh thu"])
            st.dataframe(df_rev, use_container_width=True, hide_index=True)

    # --- 8. CHATBOX NỘI BỘ ---
    elif page == "💬 Chatbox Nội bộ":
        st.title("💬 Kênh trao đổi thông tin nội bộ nhân viên")

        messages = read_df(
            "SELECT display_name AS `Người gửi`, message AS `Nội dung`, created_at AS `Thời gian` FROM chat_messages ORDER BY id DESC LIMIT 50"
        )

        for _, msg in messages.iloc[::-1].iterrows():
            with st.chat_message("user"):
                st.write(f"**{msg['Người gửi']}** *({msg['Thời gian']})*")
                st.write(msg["Nội dung"])

        if prompt := st.chat_input("Nhập tin nhắn nội bộ..."):
            execute_sql(
                "INSERT INTO chat_messages (username, display_name, message, created_at) VALUES (?, ?, ?, ?)",
                (
                    user["username"],
                    user["full_name"],
                    prompt,
                    datetime.now(),
                ),
            )
            st.rerun()

    # --- 9. TRỢ LÝ AI OPENROUTER ---
    elif page == "🌐 Trợ lý AI OpenRouter":
        st.title("🌐 Trợ lý AI Quản lý Khách sạn Thông minh")

        default_api_key = st.secrets.get("OPENROUTER_API_KEY", "")

        with st.sidebar:
            st.markdown("---")
            st.subheader("⚙️ Cấu hình OpenRouter")
            openrouter_key = st.text_input(
                "OpenRouter API Key:",
                value=default_api_key,
                type="password",
                key="openrouter_api_key_sidebar_input",
            )
            ai_model = st.selectbox(
                "Chọn mô hình AI:",
                [
                    "openrouter/free",
                    "google/gemma-4-31b-it:free",
                    "qwen/qwen3.8-27b:free",
                    "openai/gpt-4o-mini",
                ],
            )
            if st.button("🗑️ Xóa lịch sử Chat AI"):
                st.session_state["ai_messages"] = []
                st.rerun()

        for msg in st.session_state["ai_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input("Hỏi trợ lý AI về nghiệp vụ khách sạn..."):
            if not openrouter_key:
                st.error("⚠️ Vui lòng nhập OpenRouter API Key ở sidebar bên trái!")
            else:
                st.session_state["ai_messages"].append(
                    {"role": "user", "content": user_prompt}
                )
                with st.chat_message("user"):
                    st.markdown(user_prompt)

                with st.chat_message("assistant"):
                    status_placeholder = st.empty()
                    status_placeholder.markdown(
                        "🔄 *AI đang phân tích yêu cầu...*"
                    )
                    try:
                        client = openai.OpenAI(
                            base_url="https://openrouter.ai/api/v1",
                            api_key=openrouter_key,
                        )
                        messages = [
                            {
                                "role": "system",
                                "content": "Bạn là Trợ lý AI chuyên nghiệp hỗ trợ vận hành khách sạn tiêu chuẩn quốc tế.",
                            }
                        ]
                        for m in st.session_state["ai_messages"]:
                            messages.append(
                                {"role": m["role"], "content": m["content"]}
                            )

                        response = client.chat.completions.create(
                            model=ai_model, messages=messages
                        )
                        ai_reply = response.choices[0].message.content
                        status_placeholder.markdown(ai_reply)
                        st.session_state["ai_messages"].append(
                            {"role": "assistant", "content": ai_reply}
                        )
                    except Exception as e:
                        status_placeholder.error(
                            f"❌ Lỗi kết nối OpenRouter API: {e}"
                        )

    # --- 10. PHÂN QUYỀN NHÂN VIÊN ---
    elif page == "👨‍💼 Phân quyền Nhân viên":
        if not role_allowed("Quản trị viên"):
            st.error(
                "⛔ Bạn không có quyền truy cập chức năng quản trị nhân sự."
            )
        else:
            st.title("👨‍💼 Quản lý nhân viên & Phân quyền hệ thống")
            tab_list_emp, tab_add_emp = st.tabs(
                ["📋 Danh sách nhân sự", "➕ Thêm nhân sự mới"]
            )

            with tab_list_emp:
                emp_df = read_df(
                    "SELECT id AS `ID`, full_name AS `Họ tên`, username AS `Tài khoản`, role AS `Chức vụ`, phone AS `SĐT`, CASE WHEN active = 1 THEN 'Hoạt động' ELSE 'Khóa' END AS `Trạng thái` FROM employees ORDER BY id DESC"
                )
                st.dataframe(emp_df, use_container_width=True, hide_index=True)

            with tab_add_emp:
                with st.form("add_employee_form"):
                    emp_name = st.text_input("Họ tên nhân viên *")
                    emp_user = st.text_input("Tên đăng nhập *")
                    emp_pass = st.text_input("Mật khẩu *", type="password")
                    emp_role = st.selectbox("Chức vụ / Vai trò", ROLES)
                    emp_phone = st.text_input("Số điện thoại")
                    emp_submit = st.form_submit_button(
                        "💾 Thêm nhân viên", use_container_width=True
                    )

                if emp_submit:
                    if not emp_name or not emp_user or not emp_pass:
                        st.error("Vui lòng điền đầy đủ thông tin bắt buộc.")
                    else:
                        try:
                            execute_sql(
                                "INSERT INTO employees (full_name, username, password, role, phone, active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                                (
                                    emp_name.strip(),
                                    emp_user.strip(),
                                    emp_pass.strip(),
                                    emp_role,
                                    emp_phone,
                                    datetime.now(),
                                ),
                            )
                            st.success("✅ Thêm nhân sự thành công!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Tên tài khoản đã tồn tại!")


if __name__ == "__main__":
    main()
