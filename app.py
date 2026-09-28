import ssl
from datetime import date, datetime, timedelta

import pandas as pd
import pymysql
import streamlit as st
from sqlalchemy import create_engine, text


# =========================================================
# HOTEL 4 STAR - STREAMLIT + AIVEN MYSQL
# =========================================================
# This version uses the Aiven connection information supplied
# by the user and stores hotel data directly in MySQL.
# =========================================================

st.set_page_config(
    page_title="Hotel 4★ Management",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# AIVEN MYSQL CONNECTION
# =========================================================
# The values below are from the connection information supplied
# for this project.
# SSL mode is REQUIRED: TLS is forced, but certificate identity
# is not verified here. For stricter verification, add the Aiven
# CA certificate and set ssl_ca / ssl_verify_identity=True.
# =========================================================

DB_HOST = "mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com"
DB_PORT = 18185
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_dqj0WOlOyaaUQCY-wGC"
DB_NAME = "defaultdb"


def make_connection():
    """Create a fresh Aiven MySQL connection with TLS required."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        # PyMySQL uses this option to require SSL/TLS while not
        # requiring a CA file. This matches SSL mode REQUIRED.
        ssl_verify_cert=False,
    )


@st.cache_resource

def get_db():
    # Test the credentials and database immediately.
    test = make_connection()
    test.close()

    return create_engine(
        "mysql+pymysql://",
        creator=make_connection,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


try:
    DB = get_db()
except Exception as exc:
    st.error("❌ Không thể kết nối MySQL Aiven")
    st.code(str(exc))
    st.info(
        "Host / Port / User / Database đang dùng:\n"
        f"Host = {DB_HOST}\n"
        f"Port = {DB_PORT}\n"
        f"User = {DB_USER}\n"
        f"Database = {DB_NAME}\n\n"
        "Nếu vẫn là lỗi 1045 thì Aiven đang từ chối username/password "
        "của service này; lúc đó phải kiểm tra hoặc reset password trong Aiven."
    )
    st.stop()


def execute_sql(query, params=None):
    with DB.begin() as conn:
        return conn.execute(text(query), params or {})


def read_df(query, params=None):
    with DB.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


def money(value):
    return f"{float(value or 0):,.0f} VNĐ"


def log_action(username, action):
    execute_sql(
        """
        INSERT INTO audit_logs (username, action, created_at)
        VALUES (:username, :action, :created_at)
        """,
        {
            "username": username,
            "action": action,
            "created_at": datetime.now(),
        },
    )


# =========================================================
# DATABASE TABLES
# =========================================================

def create_tables():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS employees (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            username VARCHAR(80) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(60) NOT NULL,
            phone VARCHAR(30),
            active TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS guests (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(30),
            email VARCHAR(150),
            id_number VARCHAR(80),
            address VARCHAR(255),
            note TEXT,
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            room_number VARCHAR(30) NOT NULL UNIQUE,
            room_type VARCHAR(80) NOT NULL,
            floor INT NOT NULL,
            price DECIMAL(15,2) NOT NULL,
            status VARCHAR(40) NOT NULL DEFAULT 'Trống',
            note VARCHAR(255)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            guest_id BIGINT NOT NULL,
            room_id BIGINT NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            adults INT NOT NULL DEFAULT 1,
            children INT NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'Đã đặt',
            source VARCHAR(50) NOT NULL DEFAULT 'Tại quầy',
            note TEXT,
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_booking_guest
                FOREIGN KEY (guest_id) REFERENCES guests(id),
            CONSTRAINT fk_booking_room
                FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS payments (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            booking_id BIGINT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            method VARCHAR(50) NOT NULL,
            payment_type VARCHAR(50) NOT NULL DEFAULT 'Thanh toán',
            paid_at DATETIME NOT NULL,
            note VARCHAR(255),
            CONSTRAINT fk_payment_booking
                FOREIGN KEY (booking_id) REFERENCES bookings(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS housekeeping (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            room_id BIGINT NOT NULL UNIQUE,
            status VARCHAR(50) NOT NULL DEFAULT 'Sạch',
            staff VARCHAR(120) NOT NULL DEFAULT 'Chưa phân công',
            updated_at DATETIME NOT NULL,
            note VARCHAR(255),
            CONSTRAINT fk_house_room
                FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS maintenance (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            room_id BIGINT NULL,
            title VARCHAR(180) NOT NULL,
            description TEXT,
            priority VARCHAR(30) NOT NULL DEFAULT 'Trung bình',
            status VARCHAR(50) NOT NULL DEFAULT 'Mới',
            assigned_to VARCHAR(120) NOT NULL DEFAULT 'Chưa phân công',
            created_at DATETIME NOT NULL,
            completed_at DATETIME NULL,
            CONSTRAINT fk_maintenance_room
                FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80),
            action VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) NOT NULL,
            display_name VARCHAR(150) NOT NULL,
            message TEXT NOT NULL,
            created_at DATETIME NOT NULL
        )
        """,
    ]

    with DB.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


# =========================================================
# SEED DATA
# =========================================================

def seed_data():
    # Demo employees
    employee_count = int(
        read_df("SELECT COUNT(*) AS n FROM employees").iloc[0]["n"]
    )

    if employee_count == 0:
        employees = [
            ("Quản trị viên", "admin", "123456", "Quản trị viên", "0900000001"),
            ("Lễ tân", "reception", "123456", "Lễ tân", "0900000002"),
            ("Housekeeping", "housekeeping", "123456", "Housekeeping", "0900000003"),
            ("Kế toán", "accounting", "123456", "Kế toán", "0900000004"),
            ("Bảo trì", "maintenance", "123456", "Bảo trì", "0900000005"),
        ]

        with DB.begin() as conn:
            for full_name, username, password, role, phone in employees:
                conn.execute(
                    text(
                        """
                        INSERT INTO employees
                        (full_name, username, password, role, phone, active, created_at)
                        VALUES (:name, :username, :password, :role, :phone, 1, :created)
                        """
                    ),
                    {
                        "name": full_name,
                        "username": username,
                        "password": password,
                        "role": role,
                        "phone": phone,
                        "created": datetime.now(),
                    },
                )

    # Demo rooms
    room_count = int(
        read_df("SELECT COUNT(*) AS n FROM rooms").iloc[0]["n"]
    )

    if room_count == 0:
        rooms = [
            ("101", "Standard", 1, 300000),
            ("102", "Standard", 1, 300000),
            ("103", "Standard", 1, 350000),
            ("201", "Deluxe", 2, 450000),
            ("202", "Deluxe", 2, 450000),
            ("203", "Deluxe", 2, 500000),
            ("301", "VIP", 3, 600000),
            ("302", "VIP", 3, 800000),
            ("401", "President", 4, 1500000),
        ]

        with DB.begin() as conn:
            for room_number, room_type, floor, price in rooms:
                conn.execute(
                    text(
                        """
                        INSERT INTO rooms
                        (room_number, room_type, floor, price, status)
                        VALUES (:number, :type, :floor, :price, 'Trống')
                        """
                    ),
                    {
                        "number": room_number,
                        "type": room_type,
                        "floor": floor,
                        "price": price,
                    },
                )

    # Housekeeping rows for all rooms
    room_rows = read_df("SELECT id FROM rooms")
    existing_housekeeping = set(
        int(x)
        for x in read_df("SELECT room_id FROM housekeeping")["room_id"].tolist()
    )

    with DB.begin() as conn:
        for room_id in room_rows["id"].tolist():
            if int(room_id) not in existing_housekeeping:
                conn.execute(
                    text(
                        """
                        INSERT INTO housekeeping
                        (room_id, status, staff, updated_at)
                        VALUES (:room_id, 'Sạch', 'Chưa phân công', :now)
                        """
                    ),
                    {
                        "room_id": int(room_id),
                        "now": datetime.now(),
                    },
                )


try:
    create_tables()
    seed_data()
except Exception as exc:
    st.error("❌ Kết nối được MySQL nhưng khởi tạo database thất bại.")
    st.code(str(exc))
    st.stop()


# =========================================================
# DATA HELPERS
# =========================================================

ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bảo trì"]
HOUSEKEEPING_STATUSES = ["Sạch", "Cần dọn", "Đang dọn", "Đã kiểm tra"]
PAYMENT_METHODS = ["Tiền mặt", "Chuyển khoản", "Thẻ", "Ví điện tử"]
BOOKING_STATUSES = ["Đã đặt", "Đã check-in", "Đã check-out", "Đã hủy"]
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
MAINTENANCE_STATUSES = ["Mới", "Đang xử lý", "Hoàn thành", "Đã hủy"]
ROLES = ["Quản trị viên", "Lễ tân", "Housekeeping", "Kế toán", "Bảo trì"]


def get_rooms():
    return read_df(
        """
        SELECT
            r.id AS room_id,
            CONCAT('P.', r.room_number) AS `Phòng`,
            r.room_number,
            r.room_type AS `Hạng phòng`,
            r.floor AS `Tầng`,
            r.price AS `Giá/đêm`,
            r.status AS `Trạng thái`,
            COALESCE(h.status, 'Sạch') AS `Housekeeping`,
            COALESCE(h.staff, 'Chưa phân công') AS `Nhân viên`
        FROM rooms r
        LEFT JOIN housekeeping h ON h.room_id = r.id
        ORDER BY r.floor, r.room_number
        """
    )


def get_bookings():
    return read_df(
        """
        SELECT
            b.id AS `Mã đặt`,
            g.full_name AS `Khách hàng`,
            g.phone AS `SĐT`,
            CONCAT('P.', r.room_number) AS `Phòng`,
            r.room_number,
            r.room_type AS `Hạng phòng`,
            b.check_in AS `Check-in`,
            b.check_out AS `Check-out`,
            DATEDIFF(b.check_out, b.check_in) AS `Số đêm`,
            b.adults AS `Người lớn`,
            b.children AS `Trẻ em`,
            b.status AS `Trạng thái`,
            b.source AS `Nguồn`,
            COALESCE(SUM(p.amount), 0) AS `Đã thanh toán`
        FROM bookings b
        JOIN guests g ON g.id = b.guest_id
        JOIN rooms r ON r.id = b.room_id
        LEFT JOIN payments p ON p.booking_id = b.id
        GROUP BY
            b.id, g.full_name, g.phone, r.room_number, r.room_type,
            b.check_in, b.check_out, b.adults, b.children,
            b.status, b.source
        ORDER BY b.id DESC
        """
    )


def available_rooms(checkin, checkout):
    return read_df(
        """
        SELECT r.id, r.room_number, r.room_type, r.price, r.floor
        FROM rooms r
        WHERE r.status <> 'Bảo trì'
          AND NOT EXISTS (
              SELECT 1
              FROM bookings b
              WHERE b.room_id = r.id
                AND b.status IN ('Đã đặt', 'Đã check-in')
                AND b.check_in < :checkout
                AND b.check_out > :checkin
          )
        ORDER BY r.floor, r.room_number
        """,
        {"checkin": checkin, "checkout": checkout},
    )


def booking_total(booking_id):
    row = read_df(
        """
        SELECT
            DATEDIFF(b.check_out, b.check_in) AS nights,
            r.price
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE b.id = :booking_id
        """,
        {"booking_id": int(booking_id)},
    )

    if row.empty:
        return 0

    nights = max(1, int(row.iloc[0]["nights"]))
    return nights * float(row.iloc[0]["price"])


def role_allowed(*roles):
    return st.session_state.user and st.session_state.user["role"] in roles


# =========================================================
# LOGIN
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "🏠 Tổng quan"


if st.session_state.user is None:
    st.title("🏨 HOTEL 4★ MANAGEMENT")
    st.caption("Streamlit + Aiven MySQL — Quản lý khách sạn toàn diện")

    col1, col2 = st.columns([1, 1.15])

    with col1:
        st.subheader("🔐 Đăng nhập nhân viên")

        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("🚀 Đăng nhập", use_container_width=True)

        if submitted:
            user_df = read_df(
                """
                SELECT id, full_name, username, role, phone
                FROM employees
                WHERE username=:username
                  AND password=:password
                  AND active=1
                LIMIT 1
                """,
                {"username": username.strip(), "password": password},
            )

            if user_df.empty:
                st.error("❌ Sai tài khoản hoặc mật khẩu.")
            else:
                st.session_state.user = user_df.iloc[0].to_dict()
                log_action(username.strip(), "Đăng nhập hệ thống")
                st.rerun()

    with col2:
        st.info(
            """
            ### Tài khoản demo

            `admin / 123456`

            `reception / 123456`

            `housekeeping / 123456`

            `accounting / 123456`

            `maintenance / 123456`
            """
        )

    st.stop()


user = st.session_state.user


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏨 HOTEL 4★")
st.sidebar.success(
    f"👤 {user['full_name']}\n\n🔑 {user['role']}"
)
st.sidebar.caption(f"🟢 Database: {DB_NAME}")

menus = [
    "🏠 Tổng quan",
    "🛎️ Quản lý đặt phòng",
    "🚪 Check-in / Check-out",
    "👥 Quản lý khách",
    "💳 Quản lý thanh toán",
    "🧹 Housekeeping",
    "🔧 Quản lý bảo trì",
    "📊 Báo cáo doanh thu",
    "📈 Công suất phòng",
    "💬 Chatbox / Bình luận",
]

if role_allowed("Quản trị viên"):
    menus.append("👨‍💼 Phân quyền nhân viên")

for item in menus:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state.page = item

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    log_action(user["username"], "Đăng xuất hệ thống")
    st.session_state.user = None
    st.rerun()

page = st.session_state.page


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Tổng quan":
    st.title("🏨 Dashboard khách sạn 4 sao")
    st.caption(f"Xin chào {user['full_name']} — {datetime.now():%d/%m/%Y %H:%M}")

    rooms = get_rooms()
    bookings = get_bookings()

    total_rooms = len(rooms)
    occupied = int((rooms["Trạng thái"] == "Đang ở").sum())
    reserved = int((rooms["Trạng thái"] == "Đã đặt").sum())
    clean = int((rooms["Housekeeping"] == "Sạch").sum())
    maintenance = int((rooms["Trạng thái"] == "Bảo trì").sum())

    a, b, c, d, e = st.columns(5)
    a.metric("🛏️ Tổng phòng", total_rooms)
    b.metric("🔴 Đang ở", occupied)
    c.metric("🟡 Đã đặt", reserved)
    d.metric("🟢 Sạch", clean)
    e.metric("🔧 Bảo trì", maintenance)

    st.divider()

    occupancy = occupied / total_rooms * 100 if total_rooms else 0

    st.subheader("⚡ Công suất hiện tại")
    st.progress(min(1.0, occupancy / 100))
    st.write(f"**{occupancy:.1f}%** phòng đang có khách.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚨 Phòng cần xử lý")
        urgent = rooms[
            rooms["Housekeeping"].isin(["Cần dọn", "Đang dọn"])
            | rooms["Trạng thái"].eq("Bảo trì")
        ]
        st.dataframe(urgent, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🛎️ Booking mới nhất")
        st.dataframe(bookings.head(8), use_container_width=True, hide_index=True)


# =========================================================
# BOOKING
# =========================================================

elif page == "🛎️ Quản lý đặt phòng":
    st.title("🛎️ Quản lý đặt phòng")

    tab_new, tab_list = st.tabs(["➕ Tạo đặt phòng", "📋 Danh sách"])

    with tab_new:
        guests = read_df(
            "SELECT id, full_name, phone FROM guests ORDER BY full_name"
        )

        if guests.empty:
            st.warning("Chưa có khách hàng. Hãy tạo khách trước.")
        else:
            guest_map = {
                f"{row['full_name']} — {row['phone'] or 'Không có SĐT'}": int(row["id"])
                for _, row in guests.iterrows()
            }

            c1, c2 = st.columns(2)

            with c1:
                guest_label = st.selectbox("👤 Khách hàng", list(guest_map.keys()))
                checkin = st.date_input("📅 Check-in", date.today(), key="book_checkin")
                adults = st.number_input("👨 Người lớn", 1, 10, 1)
                source = st.selectbox(
                    "📱 Nguồn đặt",
                    ["Tại quầy", "Điện thoại", "Website", "OTA"],
                )

            with c2:
                checkout = st.date_input(
                    "📅 Check-out",
                    date.today() + timedelta(days=1),
                    key="book_checkout",
                )
                children = st.number_input("👶 Trẻ em", 0, 10, 0)
                note = st.text_area("📝 Ghi chú")

            if checkout <= checkin:
                st.error("Check-out phải sau Check-in.")
            else:
                available = available_rooms(checkin, checkout)

                if available.empty:
                    st.error("Không còn phòng trống trong khoảng thời gian này.")
                else:
                    room_labels = [
                        f"P.{row['room_number']} — {row['room_type']} — {money(row['price'])}/đêm"
                        for _, row in available.iterrows()
                    ]

                    selected_room = st.selectbox("🚪 Chọn phòng", room_labels)
                    idx = room_labels.index(selected_room)
                    room = available.iloc[idx]
                    nights = (checkout - checkin).days
                    total = nights * float(room["price"])

                    st.success(
                        f"Phòng P.{room['room_number']} • {nights} đêm • {money(total)}"
                    )

                    if st.button("✅ Xác nhận đặt phòng", use_container_width=True):
                        execute_sql(
                            """
                            INSERT INTO bookings
                            (guest_id, room_id, check_in, check_out,
                             adults, children, status, source, note, created_at)
                            VALUES
                            (:guest_id, :room_id, :check_in, :check_out,
                             :adults, :children, 'Đã đặt', :source, :note, :created_at)
                            """,
                            {
                                "guest_id": guest_map[guest_label],
                                "room_id": int(room["id"]),
                                "check_in": checkin,
                                "check_out": checkout,
                                "adults": int(adults),
                                "children": int(children),
                                "source": source,
                                "note": note,
                                "created_at": datetime.now(),
                            },
                        )

                        execute_sql(
                            "UPDATE rooms SET status='Đã đặt' WHERE id=:room_id",
                            {"room_id": int(room["id"])},
                        )

                        log_action(
                            user["username"],
                            f"Tạo booking P.{room['room_number']}",
                        )

                        st.success("🎉 Đặt phòng thành công!")
                        st.rerun()

    with tab_list:
        st.dataframe(get_bookings(), use_container_width=True, hide_index=True)


# =========================================================
# CHECK-IN / CHECK-OUT
# =========================================================

elif page == "🚪 Check-in / Check-out":
    st.title("🚪 Check-in / Check-out")

    bookings = get_bookings()
    active = bookings[bookings["Trạng thái"].isin(["Đã đặt", "Đã check-in"])]

    if active.empty:
        st.info("Không có booking đang chờ xử lý.")
    else:
        booking_id = st.selectbox("🧾 Mã đặt phòng", active["Mã đặt"].tolist())
        row = active[active["Mã đặt"] == booking_id].iloc[0]

        a, b, c = st.columns(3)
        a.metric("👤 Khách", row["Khách hàng"])
        b.metric("🚪 Phòng", row["Phòng"])
        c.metric("📌 Trạng thái", row["Trạng thái"])

        if row["Trạng thái"] == "Đã đặt":
            if st.button("🟢 CHECK-IN", use_container_width=True):
                execute_sql(
                    "UPDATE bookings SET status='Đã check-in' WHERE id=:id",
                    {"id": int(booking_id)},
                )
                execute_sql(
                    "UPDATE rooms SET status='Đang ở' WHERE room_number=:room",
                    {"room": row["room_number"]},
                )
                log_action(user["username"], f"Check-in booking #{booking_id}")
                st.success("✅ Check-in thành công!")
                st.rerun()

        if row["Trạng thái"] == "Đã check-in":
            if st.button("🔵 CHECK-OUT", use_container_width=True):
                execute_sql(
                    "UPDATE bookings SET status='Đã check-out' WHERE id=:id",
                    {"id": int(booking_id)},
                )
                execute_sql(
                    "UPDATE rooms SET status='Trống' WHERE room_number=:room",
                    {"room": row["room_number"]},
                )
                room_id_row = read_df(
                    "SELECT id FROM rooms WHERE room_number=:room",
                    {"room": row["room_number"]},
                )
                if not room_id_row.empty:
                    execute_sql(
                        """
                        UPDATE housekeeping
                        SET status='Cần dọn', updated_at=:updated_at
                        WHERE room_id=:room_id
                        """,
                        {
                            "updated_at": datetime.now(),
                            "room_id": int(room_id_row.iloc[0]["id"]),
                        },
                    )
                log_action(user["username"], f"Check-out booking #{booking_id}")
                st.success("✅ Check-out thành công. Phòng đã chuyển sang Cần dọn.")
                st.rerun()


# =========================================================
# GUESTS
# =========================================================

elif page == "👥 Quản lý khách":
    st.title("👥 Quản lý thông tin khách")

    tab1, tab2 = st.tabs(["➕ Thêm khách", "📋 Danh sách khách"])

    with tab1:
        with st.form("guest_form"):
            name = st.text_input("Họ và tên *")
            phone = st.text_input("Số điện thoại")
            email = st.text_input("Email")
            id_number = st.text_input("CCCD / Hộ chiếu")
            address = st.text_input("Địa chỉ")
            note = st.text_area("Ghi chú")
            submit = st.form_submit_button("💾 Lưu khách hàng", use_container_width=True)

        if submit:
            if not name.strip():
                st.error("Vui lòng nhập họ tên.")
            else:
                execute_sql(
                    """
                    INSERT INTO guests
                    (full_name, phone, email, id_number, address, note, created_at)
                    VALUES (:name, :phone, :email, :id_number, :address, :note, :created_at)
                    """,
                    {
                        "name": name.strip(),
                        "phone": phone,
                        "email": email,
                        "id_number": id_number,
                        "address": address,
                        "note": note,
                        "created_at": datetime.now(),
                    },
                )
                log_action(user["username"], f"Thêm khách {name}")
                st.success("✅ Đã lưu hồ sơ khách.")
                st.rerun()

    with tab2:
        guest_df = read_df(
            """
            SELECT
                id AS `ID`,
                full_name AS `Họ tên`,
                phone AS `SĐT`,
                email AS `Email`,
                id_number AS `CCCD/Hộ chiếu`,
                address AS `Địa chỉ`,
                note AS `Ghi chú`
            FROM guests
            ORDER BY id DESC
            """
        )
        st.dataframe(guest_df, use_container_width=True, hide_index=True)


# =========================================================
# PAYMENTS
# =========================================================

elif page == "💳 Quản lý thanh toán":
    st.title("💳 Quản lý thanh toán")

    bookings = get_bookings()
    active = bookings[bookings["Trạng thái"].isin(["Đã đặt", "Đã check-in"])]

    if active.empty:
        st.info("Không có booking cần thanh toán.")
    else:
        booking_id = st.selectbox("🧾 Mã đặt phòng", active["Mã đặt"].tolist())
        row = active[active["Mã đặt"] == booking_id].iloc[0]
        total = booking_total(booking_id)
        paid = float(row["Đã thanh toán"] or 0)
        remaining = max(0, total - paid)

        a, b, c = st.columns(3)
        a.metric("💰 Tổng tiền", money(total))
        b.metric("💵 Đã trả", money(paid))
        c.metric("🧾 Còn lại", money(remaining))

        amount = st.number_input(
            "Số tiền thanh toán",
            min_value=0.0,
            max_value=float(remaining),
            value=float(remaining),
            step=50000.0,
        )
        method = st.selectbox("Phương thức", PAYMENT_METHODS)
        payment_type = st.selectbox("Loại giao dịch", ["Đặt cọc", "Thanh toán"])
        note = st.text_input("Ghi chú")

        if st.button("💰 Ghi nhận thanh toán", use_container_width=True):
            if amount <= 0:
                st.error("Số tiền phải lớn hơn 0.")
            else:
                execute_sql(
                    """
                    INSERT INTO payments
                    (booking_id, amount, method, payment_type, paid_at, note)
                    VALUES (:booking_id, :amount, :method, :payment_type, :paid_at, :note)
                    """,
                    {
                        "booking_id": int(booking_id),
                        "amount": amount,
                        "method": method,
                        "payment_type": payment_type,
                        "paid_at": datetime.now(),
                        "note": note,
                    },
                )
                log_action(user["username"], f"Thanh toán {money(amount)} booking #{booking_id}")
                st.success("✅ Đã ghi nhận thanh toán.")
                st.rerun()

    st.divider()
    st.subheader("📋 Lịch sử giao dịch")
    st.dataframe(
        read_df(
            """
            SELECT
                p.id AS `ID`,
                p.booking_id AS `Mã đặt`,
                g.full_name AS `Khách`,
                p.amount AS `Số tiền`,
                p.method AS `Phương thức`,
                p.payment_type AS `Loại`,
                p.paid_at AS `Thời gian`,
                p.note AS `Ghi chú`
            FROM payments p
            JOIN bookings b ON b.id=p.booking_id
            JOIN guests g ON g.id=b.guest_id
            ORDER BY p.id DESC
            """
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# HOUSEKEEPING
# =========================================================

elif page == "🧹 Housekeeping":
    st.title("🧹 Quản lý Housekeeping")

    rooms = get_rooms()
    st.dataframe(rooms, use_container_width=True, hide_index=True)
    st.divider()

    selected_room = st.selectbox("🚪 Chọn phòng", rooms["Phòng"].tolist())
    current = rooms[rooms["Phòng"] == selected_room].iloc[0]

    status = st.selectbox(
        "Trạng thái vệ sinh",
        HOUSEKEEPING_STATUSES,
        index=(
            HOUSEKEEPING_STATUSES.index(current["Housekeeping"])
            if current["Housekeeping"] in HOUSEKEEPING_STATUSES
            else 0
        ),
    )
    staff = st.text_input("👷 Nhân viên", current["Nhân viên"])
    note = st.text_input("📝 Ghi chú")

    if st.button("💾 Lưu cập nhật", use_container_width=True):
        execute_sql(
            """
            UPDATE housekeeping
            SET status=:status, staff=:staff, updated_at=:updated_at, note=:note
            WHERE room_id=:room_id
            """,
            {
                "status": status,
                "staff": staff,
                "updated_at": datetime.now(),
                "note": note,
                "room_id": int(current["room_id"]),
            },
        )
        log_action(user["username"], f"Housekeeping {selected_room}: {status}")
        st.success("✅ Đã cập nhật Housekeeping.")
        st.rerun()


# =========================================================
# MAINTENANCE
# =========================================================

elif page == "🔧 Quản lý bảo trì":
    st.title("🔧 Quản lý bảo trì")

    tab_new, tab_list = st.tabs(["➕ Tạo phiếu", "📋 Danh sách"])

    with tab_new:
        rooms = read_df("SELECT id, room_number FROM rooms ORDER BY room_number")
        room_options = ["Toàn khách sạn"] + [f"P.{x}" for x in rooms["room_number"].tolist()]

        with st.form("maintenance_form"):
            room_label = st.selectbox("🚪 Phòng", room_options)
            title = st.text_input("Tiêu đề lỗi *")
            description = st.text_area("Mô tả")
            priority = st.selectbox("Mức độ", PRIORITIES)
            assigned = st.text_input("Nhân viên xử lý", "Chưa phân công")
            submit = st.form_submit_button("🛠️ Tạo phiếu", use_container_width=True)

        if submit:
            if not title.strip():
                st.error("Vui lòng nhập tiêu đề lỗi.")
            else:
                room_id = None
                if room_label != "Toàn khách sạn":
                    number = room_label.replace("P.", "")
                    match = rooms[rooms["room_number"] == number]
                    if not match.empty:
                        room_id = int(match.iloc[0]["id"])

                execute_sql(
                    """
                    INSERT INTO maintenance
                    (room_id, title, description, priority, status, assigned_to, created_at)
                    VALUES (:room_id, :title, :description, :priority,
                            'Mới', :assigned_to, :created_at)
                    """,
                    {
                        "room_id": room_id,
                        "title": title,
                        "description": description,
                        "priority": priority,
                        "assigned_to": assigned,
                        "created_at": datetime.now(),
                    },
                )

                if room_id is not None:
                    execute_sql(
                        "UPDATE rooms SET status='Bảo trì' WHERE id=:room_id",
                        {"room_id": room_id},
                    )

                log_action(user["username"], f"Tạo phiếu bảo trì: {title}")
                st.success("✅ Đã tạo phiếu bảo trì.")
                st.rerun()

    with tab_list:
        maintenance = read_df(
            """
            SELECT
                m.id AS `ID`,
                COALESCE(CONCAT('P.', r.room_number), 'Toàn khách sạn') AS `Phòng`,
                m.title AS `Tiêu đề`,
                m.description AS `Mô tả`,
                m.priority AS `Mức độ`,
                m.status AS `Trạng thái`,
                m.assigned_to AS `Nhân viên`,
                m.created_at AS `Tạo lúc`,
                m.completed_at AS `Hoàn thành`
            FROM maintenance m
            LEFT JOIN rooms r ON r.id=m.room_id
            ORDER BY m.id DESC
            """
        )

        st.dataframe(maintenance, use_container_width=True, hide_index=True)

        if not maintenance.empty:
            ticket = st.selectbox("Chọn phiếu", maintenance["ID"].tolist())
            new_status = st.selectbox("Trạng thái mới", MAINTENANCE_STATUSES)

            if st.button("💾 Cập nhật phiếu"):
                completed_at = datetime.now() if new_status == "Hoàn thành" else None
                execute_sql(
                    """
                    UPDATE maintenance
                    SET status=:status, completed_at=:completed_at
                    WHERE id=:id
                    """,
                    {
                        "status": new_status,
                        "completed_at": completed_at,
                        "id": int(ticket),
                    },
                )

                row = maintenance[maintenance["ID"] == ticket].iloc[0]
                if row["Phòng"] != "Toàn khách sạn" and new_status == "Hoàn thành":
                    room_number = str(row["Phòng"]).replace("P.", "")
                    execute_sql(
                        "UPDATE rooms SET status='Trống' WHERE room_number=:room_number",
                        {"room_number": room_number},
                    )

                log_action(user["username"], f"Cập nhật bảo trì #{ticket}")
                st.success("✅ Đã cập nhật phiếu.")
                st.rerun()


# =========================================================
# REVENUE
# =========================================================

elif page == "📊 Báo cáo doanh thu":
    st.title("📊 Báo cáo doanh thu")

    payments = read_df(
        """
        SELECT
            DATE(p.paid_at) AS `Ngày`,
            p.amount AS `Doanh thu`,
            p.method AS `Phương thức`,
            p.payment_type AS `Loại`,
            g.full_name AS `Khách`
        FROM payments p
        JOIN bookings b ON b.id=p.booking_id
        JOIN guests g ON g.id=b.guest_id
        WHERE p.payment_type <> 'Hoàn tiền'
        ORDER BY p.paid_at DESC
        """
    )

    if payments.empty:
        st.info("Chưa có dữ liệu doanh thu.")
    else:
        payments["Ngày"] = pd.to_datetime(payments["Ngày"])
        payments["Doanh thu"] = pd.to_numeric(payments["Doanh thu"], errors="coerce").fillna(0)

        start = st.date_input("Từ ngày", date.today() - timedelta(days=30))
        end = st.date_input("Đến ngày", date.today())

        filtered = payments[
            (payments["Ngày"].dt.date >= start)
            & (payments["Ngày"].dt.date <= end)
        ]

        revenue = filtered["Doanh thu"].sum()
        transaction_count = len(filtered)

        a, b = st.columns(2)
        a.metric("💰 Tổng doanh thu", money(revenue))
        b.metric("🧾 Số giao dịch", transaction_count)

        daily = (
            filtered.groupby(filtered["Ngày"].dt.date)["Doanh thu"]
            .sum()
            .reset_index()
        )
        daily.columns = ["Ngày", "Doanh thu"]

        st.subheader("📈 Doanh thu theo ngày")
        if not daily.empty:
            st.line_chart(daily.set_index("Ngày"))

        st.subheader("💳 Theo phương thức thanh toán")
        method_df = (
            filtered.groupby("Phương thức")["Doanh thu"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        st.dataframe(method_df, use_container_width=True, hide_index=True)


# =========================================================
# OCCUPANCY
# =========================================================

elif page == "📈 Công suất phòng":
    st.title("📈 Thống kê công suất phòng")

    rooms = read_df("SELECT id, room_number, room_type, price FROM rooms")
    total_rooms = len(rooms)

    start = st.date_input(
        "Ngày bắt đầu",
        date.today() - timedelta(days=30),
        key="occ_start",
    )
    end = st.date_input(
        "Ngày kết thúc",
        date.today(),
        key="occ_end",
    )

    if end < start:
        st.error("Khoảng ngày không hợp lệ.")
    else:
        days = (end - start).days + 1
        end_plus = end + timedelta(days=1)

        booked_nights = float(
            read_df(
                """
                SELECT COALESCE(
                    SUM(
                        DATEDIFF(
                            LEAST(check_out, :end_plus),
                            GREATEST(check_in, :start)
                        )
                    ), 0
                ) AS nights
                FROM bookings
                WHERE status <> 'Đã hủy'
                  AND check_in < :end_plus
                  AND check_out > :start
                """,
                {"start": start, "end_plus": end_plus},
            ).iloc[0]["nights"]
        )

        capacity = total_rooms * days
        occupancy = booked_nights / capacity * 100 if capacity else 0

        a, b, c = st.columns(3)
        a.metric("🛏️ Tổng phòng", total_rooms)
        b.metric("📅 Số ngày", days)
        c.metric("📊 Công suất", f"{occupancy:.1f}%")
        st.progress(min(1.0, occupancy / 100))

        by_type = read_df(
            """
            SELECT
                r.room_type AS `Hạng phòng`,
                COUNT(DISTINCT r.id) AS `Số phòng`,
                COALESCE(
                    SUM(
                        DATEDIFF(
                            LEAST(b.check_out, :end_plus),
                            GREATEST(b.check_in, :start)
                        )
                    ), 0
                ) AS `Đêm đã bán`
            FROM rooms r
            LEFT JOIN bookings b
                ON b.room_id=r.id
               AND b.status <> 'Đã hủy'
               AND b.check_in < :end_plus
               AND b.check_out > :start
            GROUP BY r.room_type
            ORDER BY r.room_type
            """,
            {"start": start, "end_plus": end_plus},
        )

        st.subheader("🏨 Công suất theo hạng phòng")
        st.dataframe(by_type, use_container_width=True, hide_index=True)


# =========================================================
# CHATBOX / COMMENTS
# =========================================================

elif page == "💬 Chatbox / Bình luận":
    st.title("💬 Chatbox nội bộ khách sạn")
    st.caption("Nhân viên có thể để lại bình luận, thông báo hoặc trao đổi nhanh.")

    st.subheader("📝 Viết bình luận")

    with st.form("chat_form", clear_on_submit=True):
        message = st.text_area(
            "Nội dung",
            placeholder="Ví dụ: P.302 đã dọn xong, có thể nhận khách.",
        )
        send = st.form_submit_button(
            "💬 Gửi bình luận",
            use_container_width=True,
        )

    if send:
        if not message.strip():
            st.warning("Bạn chưa nhập nội dung.")
        else:
            execute_sql(
                """
                INSERT INTO chat_messages
                (username, display_name, message, created_at)
                VALUES (:username, :display_name, :message, :created_at)
                """,
                {
                    "username": user["username"],
                    "display_name": user["full_name"],
                    "message": message.strip(),
                    "created_at": datetime.now(),
                },
            )
            log_action(user["username"], "Gửi bình luận chatbox")
            st.success("✅ Đã gửi bình luận.")
            st.rerun()

    st.divider()
    st.subheader("💭 Trao đổi gần đây")

    comments = read_df(
        """
        SELECT
            display_name AS `Nhân viên`,
            message AS `Bình luận`,
            created_at AS `Thời gian`
        FROM chat_messages
        ORDER BY id DESC
        LIMIT 100
        """
    )

    if comments.empty:
        st.info("Chưa có bình luận nào.")
    else:
        for _, row in comments.iterrows():
            st.markdown(
                f"**{row['Nhân viên']}** · `{row['Thời gian']}`\n\n"
                f"> {row['Bình luận']}"
            )
            st.divider()


# =========================================================
# ROLE MANAGEMENT
# =========================================================

elif page == "👨‍💼 Phân quyền nhân viên":
    if not role_allowed("Quản trị viên"):
        st.error("⛔ Bạn không có quyền truy cập chức năng này.")
        st.stop()

    st.title("👨‍💼 Phân quyền nhân viên")

    employees = read_df(
        """
        SELECT
            id AS `ID`,
            full_name AS `Họ tên`,
            username AS `Tài khoản`,
            role AS `Vai trò`,
            phone AS `SĐT`,
            active AS `Đang hoạt động`
        FROM employees
        ORDER BY id
        """
    )
    st.dataframe(employees, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("➕ Tạo tài khoản nhân viên")

    with st.form("employee_form"):
        full_name = st.text_input("Họ tên")
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        role = st.selectbox("Vai trò", ROLES)
        phone = st.text_input("Số điện thoại")
        submit = st.form_submit_button("💾 Tạo tài khoản", use_container_width=True)

    if submit:
        if not full_name.strip() or not username.strip() or not password:
            st.error("Vui lòng nhập đầy đủ thông tin.")
        else:
            try:
                execute_sql(
                    """
                    INSERT INTO employees
                    (full_name, username, password, role, phone, active, created_at)
                    VALUES (:full_name, :username, :password, :role, :phone, 1, :created_at)
                    """,
                    {
                        "full_name": full_name.strip(),
                        "username": username.strip(),
                        "password": password,
                        "role": role,
                        "phone": phone,
                        "created_at": datetime.now(),
                    },
                )
                log_action(user["username"], f"Tạo tài khoản {username}")
                st.success("✅ Đã tạo tài khoản.")
                st.rerun()
            except Exception as exc:
                st.error("❌ Không thể tạo tài khoản.")
                st.code(str(exc))

    st.subheader("🔄 Khóa / mở tài khoản")

    if not employees.empty:
        employee_id = st.selectbox(
            "Chọn ID nhân viên",
            employees["ID"].tolist(),
        )
        active_value = st.selectbox(
            "Trạng thái",
            [1, 0],
            format_func=lambda x: "🟢 Hoạt động" if x else "🔴 Đã khóa",
        )

        if st.button("💾 Cập nhật quyền truy cập"):
            execute_sql(
                "UPDATE employees SET active=:active WHERE id=:id",
                {
                    "active": int(active_value),
                    "id": int(employee_id),
                },
            )
            log_action(user["username"], f"Đổi trạng thái tài khoản #{employee_id}")
            st.success("✅ Đã cập nhật.")
            st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()
st.sidebar.caption("🏨 Hotel 4★ Management")
st.sidebar.caption("Streamlit • Python • Aiven MySQL")
