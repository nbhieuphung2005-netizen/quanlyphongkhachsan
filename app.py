import os
from datetime import datetime, date, timedelta

import pandas as pd
import pymysql
import streamlit as st
from sqlalchemy import create_engine, text


# =========================================================
#  KHÁCH SẠN 4 SAO - HỆ THỐNG QUẢN LÝ TOÀN DIỆN
#  Streamlit + Aiven MySQL
# =========================================================

st.set_page_config(
    page_title="Hotel 4★ Management",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# AIVEN CONFIG
# Password is intentionally NOT hard-coded because it was
# exposed in the previous message. Put it in Streamlit
# Secrets or an environment variable.
#
# .streamlit/secrets.toml
# [aiven_mysql]
# password = "YOUR_CURRENT_AIVEN_PASSWORD"
# ---------------------------------------------------------
DB_HOST = os.getenv(
    "AIVEN_HOST",
    "mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com",
)
DB_PORT = int(os.getenv("AIVEN_PORT", "18185"))
DB_USER = os.getenv("AIVEN_USER", "avnadmin")
DB_NAME = os.getenv("AIVEN_DATABASE", "defaultdb")

try:
    DB_PASSWORD = st.secrets["aiven_mysql"]["AVNS_NYGYHQq39WTXGmCOttF"]
except Exception:
    DB_PASSWORD = os.getenv("AIVEN_PASSWORD", "")

if not DB_PASSWORD:
    st.error(
        "Chưa có mật khẩu Aiven. Hãy tạo .streamlit/secrets.toml "
        "với [aiven_mysql] password = \"...\" hoặc đặt biến AIVEN_PASSWORD."
    )
    st.stop()


# =========================================================
# DATABASE
# =========================================================
@st.cache_resource
def get_database():
    def connect():
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            ssl={},
            connect_timeout=20,
        )

    # Test connection first.
    test = connect()
    test.close()

    return create_engine(
        "mysql+pymysql://",
        creator=connect,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


try:
    DB = get_database()
except Exception as e:
    st.error("❌ Không thể kết nối MySQL Aiven")
    st.code(str(e))
    st.stop()


def sql(query, params=None):
    with DB.begin() as conn:
        return conn.execute(text(query), params or {})


def read_df(query, params=None):
    with DB.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


# =========================================================
# DATABASE SCHEMA
# =========================================================
def create_tables():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS employees (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            username VARCHAR(80) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
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
            status VARCHAR(40) NOT NULL DEFAULT 'Đã đặt',
            source VARCHAR(50) DEFAULT 'Tại quầy',
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
            method VARCHAR(40) NOT NULL,
            payment_type VARCHAR(40) NOT NULL DEFAULT 'Thanh toán',
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
            status VARCHAR(40) NOT NULL DEFAULT 'Sạch',
            staff VARCHAR(120) DEFAULT 'Chưa phân công',
            updated_at DATETIME NOT NULL,
            note VARCHAR(255),
            CONSTRAINT fk_house_room
                FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS maintenance (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            room_id BIGINT,
            title VARCHAR(180) NOT NULL,
            description TEXT,
            priority VARCHAR(30) NOT NULL DEFAULT 'Trung bình',
            status VARCHAR(40) NOT NULL DEFAULT 'Mới',
            assigned_to VARCHAR(120) DEFAULT 'Chưa phân công',
            created_at DATETIME NOT NULL,
            completed_at DATETIME,
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
    ]

    with DB.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def seed_data():
    # Default employees. For a school demo only; change passwords later.
    employee_count = read_df("SELECT COUNT(*) AS n FROM employees").iloc[0]["n"]
    if int(employee_count) == 0:
        employees = [
            ("admin", "123456", "Quản trị viên", "0900000001"),
            ("reception", "123456", "Lễ tân", "0900000002"),
            ("housekeeping", "123456", "Housekeeping", "0900000003"),
            ("accounting", "123456", "Kế toán", "0900000004"),
            ("maintenance", "123456", "Bảo trì", "0900000005"),
        ]
        with DB.begin() as conn:
            for username, password, role, phone in employees:
                conn.execute(
                    text("""
                        INSERT INTO employees
                        (full_name, username, password, role, phone, active, created_at)
                        VALUES (:name, :username, :password, :role, :phone, 1, :created)
                    """),
                    {
                        "name": username.title(),
                        "username": username,
                        "password": password,
                        "role": role,
                        "phone": phone,
                        "created": datetime.now(),
                    },
                )

    room_count = int(read_df("SELECT COUNT(*) AS n FROM rooms").iloc[0]["n"])
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
            for number, room_type, floor, price in rooms:
                conn.execute(
                    text("""
                        INSERT INTO rooms
                        (room_number, room_type, floor, price, status)
                        VALUES (:number, :type, :floor, :price, 'Trống')
                    """),
                    {
                        "number": number,
                        "type": room_type,
                        "floor": floor,
                        "price": price,
                    },
                )

    house_count = int(read_df("SELECT COUNT(*) AS n FROM housekeeping").iloc[0]["n"])
    if house_count == 0:
        rooms = read_df("SELECT id FROM rooms")
        with DB.begin() as conn:
            for room_id in rooms["id"]:
                conn.execute(
                    text("""
                        INSERT INTO housekeeping
                        (room_id, status, staff, updated_at)
                        VALUES (:room_id, 'Sạch', 'Chưa phân công', :now)
                    """),
                    {"room_id": int(room_id), "now": datetime.now()},
                )


try:
    create_tables()
    seed_data()
except Exception as e:
    st.error("❌ Kết nối được MySQL nhưng khởi tạo dữ liệu thất bại.")
    st.code(str(e))
    st.stop()


# =========================================================
# HELPERS
# =========================================================
ROOM_TYPES = ["Standard", "Deluxe", "VIP", "President"]
ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bảo trì"]
HOUSE_STATUSES = ["Sạch", "Cần dọn", "Đang dọn", "Đã kiểm tra"]
PAYMENT_METHODS = ["Tiền mặt", "Chuyển khoản", "Thẻ", "Ví điện tử"]
BOOKING_STATUSES = ["Đã đặt", "Đã check-in", "Đã check-out", "Đã hủy"]
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
MAINTENANCE_STATUSES = ["Mới", "Đang xử lý", "Hoàn thành", "Đã hủy"]


def log_action(username, action):
    sql(
        """
        INSERT INTO audit_logs (username, action, created_at)
        VALUES (:username, :action, :created)
        """,
        {"username": username, "action": action, "created": datetime.now()},
    )


def get_employee(username, password):
    df = read_df(
        """
        SELECT id, full_name, username, role, phone
        FROM employees
        WHERE username = :username AND password = :password AND active = 1
        LIMIT 1
        """,
        {"username": username, "password": password},
    )
    return None if df.empty else df.iloc[0].to_dict()


def money(value):
    return f"{float(value or 0):,.0f} VNĐ"


def room_data():
    return read_df(
        """
        SELECT
            r.id AS room_id,
            r.room_number AS `Phòng`,
            r.room_type AS `Hạng phòng`,
            r.floor AS `Tầng`,
            r.price AS `Giá/đêm`,
            r.status AS `Trạng thái`,
            COALESCE(h.status, 'Sạch') AS `Housekeeping`,
            COALESCE(h.staff, 'Chưa phân công') AS `Nhân viên dọn`
        FROM rooms r
        LEFT JOIN housekeeping h ON h.room_id = r.id
        ORDER BY r.floor, r.room_number
        """
    )


def available_rooms(checkin, checkout):
    return read_df(
        """
        SELECT r.*
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


def booking_data():
    return read_df(
        """
        SELECT
            b.id AS `Mã đặt`,
            g.full_name AS `Khách hàng`,
            g.phone AS `SĐT`,
            r.room_number AS `Phòng`,
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
        GROUP BY b.id, g.full_name, g.phone, r.room_number, r.room_type,
                 b.check_in, b.check_out, b.adults, b.children,
                 b.status, b.source
        ORDER BY b.id DESC
        """
    )


def booking_total(booking_id):
    row = read_df(
        """
        SELECT
            DATEDIFF(b.check_out, b.check_in) AS nights,
            r.price
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        WHERE b.id = :id
        """,
        {"id": int(booking_id)},
    )
    if row.empty:
        return 0
    return max(1, int(row.iloc[0]["nights"])) * float(row.iloc[0]["price"])


# =========================================================
# SESSION / LOGIN
# =========================================================
if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "🏠 Tổng quan"


def can(*roles):
    return st.session_state.user and st.session_state.user["role"] in roles


# =========================================================
# LOGIN
# =========================================================
if not st.session_state.user:
    st.title("🏨 HOTEL 4★ MANAGEMENT")
    st.caption("Hệ thống quản lý khách sạn bằng Streamlit + Aiven MySQL")

    left, right = st.columns([1, 1.2])

    with left:
        st.subheader("🔐 Đăng nhập nhân viên")
        with st.form("login"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập", use_container_width=True)

        if submit:
            user = get_employee(username.strip(), password)
            if user:
                st.session_state.user = user
                log_action(user["username"], "Đăng nhập hệ thống")
                st.rerun()
            else:
                st.error("Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa.")

    with right:
        st.info(
            """
            **Tài khoản demo mặc định**

            - admin / 123456
            - reception / 123456
            - housekeeping / 123456
            - accounting / 123456
            - maintenance / 123456

            Có thể đổi tài khoản sau khi đăng nhập bằng quyền quản trị.
            """
        )
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================
user = st.session_state.user

st.sidebar.title("🏨 KHÁCH SẠN 4★")
st.sidebar.success(f"👤 {user['full_name']}\n\n🔑 {user['role']}")

menus = [
    ("🏠 Tổng quan", True),
    ("🛎️ Quản lý đặt phòng", True),
    ("🚪 Check-in / Check-out", True),
    ("👥 Quản lý khách", True),
    ("💳 Quản lý thanh toán", True),
    ("🧹 Housekeeping", True),
    ("🔧 Bảo trì", True),
    ("📊 Báo cáo doanh thu", True),
    ("📈 Công suất phòng", True),
    ("👨‍💼 Phân quyền nhân viên", can("Quản trị viên")),
]

for label, allowed in menus:
    if allowed and st.sidebar.button(label, use_container_width=True):
        st.session_state.page = label

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

    rooms = room_data()
    bookings = booking_data()

    total_rooms = len(rooms)
    occupied = len(rooms[rooms["Trạng thái"] == "Đang ở"])
    reserved = len(rooms[rooms["Trạng thái"] == "Đã đặt"])
    clean = len(rooms[rooms["Housekeeping"] == "Sạch"])
    maintenance = len(rooms[rooms["Trạng thái"] == "Bảo trì"])

    a, b, c, d, e = st.columns(5)
    a.metric("🛏️ Tổng phòng", total_rooms)
    b.metric("🔴 Đang ở", occupied)
    c.metric("🟡 Đã đặt", reserved)
    d.metric("🟢 Sạch", clean)
    e.metric("🔧 Bảo trì", maintenance)

    st.divider()

    if total_rooms:
        occupancy = occupied / total_rooms * 100
        st.subheader("⚡ Công suất phòng hiện tại")
        st.progress(min(1.0, occupancy / 100))
        st.write(f"**{occupancy:.1f}%** phòng đang có khách")

    st.subheader("🧠 Bảng điều hành thông minh")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Phòng cần xử lý ngay**")
        urgent = rooms[
            rooms["Housekeeping"].isin(["Cần dọn", "Đang dọn"])
            | rooms["Trạng thái"].eq("Bảo trì")
        ]
        st.dataframe(urgent, use_container_width=True, hide_index=True)

    with col2:
        st.write("**Đặt phòng gần nhất**")
        st.dataframe(bookings.head(8), use_container_width=True, hide_index=True)


# =========================================================
# BOOKING
# =========================================================
elif page == "🛎️ Quản lý đặt phòng":
    st.title("🛎️ Quản lý đặt phòng")

    tab1, tab2 = st.tabs(["➕ Tạo đặt phòng", "📋 Danh sách đặt phòng"])

    with tab1:
        guests = read_df("SELECT id, full_name, phone FROM guests ORDER BY full_name")

        if guests.empty:
            st.warning("Chưa có khách. Hãy tạo khách ở mục 👥 Quản lý khách trước.")
        else:
            with st.form("new_booking"):
                guest_map = {
                    f"{r['full_name']} — {r['phone'] or 'Không có SĐT'}": int(r["id"])
                    for _, r in guests.iterrows()
                }

                guest_label = st.selectbox("👤 Khách hàng", list(guest_map.keys()))
                checkin = st.date_input("📅 Ngày check-in", value=date.today())
                checkout = st.date_input("📅 Ngày check-out", value=date.today() + timedelta(days=1))
                adults = st.number_input("Người lớn", 1, 10, 1)
                children = st.number_input("Trẻ em", 0, 10, 0)
                source = st.selectbox("Nguồn đặt", ["Tại quầy", "Điện thoại", "Website", "OTA"])
                note = st.text_area("Ghi chú")
                submit = st.form_submit_button("✅ Tạo đặt phòng", use_container_width=True)

            if submit:
                if checkout <= checkin:
                    st.error("Ngày check-out phải sau ngày check-in.")
                else:
                    rooms = available_rooms(checkin, checkout)
                    if rooms.empty:
                        st.error("Không còn phòng trống trong khoảng thời gian này.")
                    else:
                        room_labels = [
                            f"P.{r['room_number']} — {r['room_type']} — {money(r['price'])}"
                            for _, r in rooms.iterrows()
                        ]
                        selected = st.selectbox(
                            "Chọn phòng còn trống",
                            room_labels,
                            key="booking_room_select",
                        )

                        # The form has already submitted, so selected room is
                        # rendered here; user can choose and submit again.
                        if st.button("💾 Xác nhận phòng đã chọn", use_container_width=True):
                            room_index = room_labels.index(selected)
                            room = rooms.iloc[room_index]

                            sql(
                                """
                                INSERT INTO bookings
                                (guest_id, room_id, check_in, check_out, adults,
                                 children, status, source, note, created_at)
                                VALUES
                                (:guest, :room, :checkin, :checkout, :adults,
                                 :children, 'Đã đặt', :source, :note, :created)
                                """,
                                {
                                    "guest": guest_map[guest_label],
                                    "room": int(room["id"]),
                                    "checkin": checkin,
                                    "checkout": checkout,
                                    "adults": int(adults),
                                    "children": int(children),
                                    "source": source,
                                    "note": note,
                                    "created": datetime.now(),
                                },
                            )
                            sql(
                                "UPDATE rooms SET status='Đã đặt' WHERE id=:id",
                                {"id": int(room["id"])},
                            )
                            log_action(user["username"], f"Tạo booking phòng {room['room_number']}")
                            st.success("🎉 Đặt phòng thành công!")
                            st.rerun()

    with tab2:
        st.dataframe(booking_data(), use_container_width=True, hide_index=True)


# =========================================================
# CHECK-IN / CHECK-OUT
# =========================================================
elif page == "🚪 Check-in / Check-out":
    st.title("🚪 Check-in / Check-out")

    bookings = booking_data()
    active = bookings[bookings["Trạng thái"].isin(["Đã đặt", "Đã check-in"])]

    if active.empty:
        st.info("Không có đặt phòng đang chờ xử lý.")
    else:
        selected_id = st.selectbox("Chọn mã đặt phòng", active["Mã đặt"].tolist())
        row = active[active["Mã đặt"] == selected_id].iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Khách", row["Khách hàng"])
        c2.metric("Phòng", row["Phòng"])
        c3.metric("Trạng thái", row["Trạng thái"])

        if row["Trạng thái"] == "Đã đặt":
            if st.button("🟢 Xác nhận CHECK-IN", use_container_width=True):
                sql(
                    "UPDATE bookings SET status='Đã check-in' WHERE id=:id",
                    {"id": int(selected_id)},
                )
                sql(
                    "UPDATE rooms SET status='Đang ở' "
                    "WHERE room_number=:room",
                    {"room": row["Phòng"]},
                )
                log_action(user["username"], f"Check-in booking #{selected_id}")
                st.success("Check-in thành công!")
                st.rerun()

        if row["Trạng thái"] == "Đã check-in":
            if st.button("🔵 Xác nhận CHECK-OUT", use_container_width=True):
                sql(
                    "UPDATE bookings SET status='Đã check-out' WHERE id=:id",
                    {"id": int(selected_id)},
                )
                sql(
                    "UPDATE rooms SET status='Trống' WHERE room_number=:room",
                    {"room": row["Phòng"]},
                )
                room_id = read_df(
                    "SELECT id FROM rooms WHERE room_number=:room",
                    {"room": row["Phòng"]},
                ).iloc[0]["id"]
                sql(
                    """
                    UPDATE housekeeping
                    SET status='Cần dọn', updated_at=:now
                    WHERE room_id=:room
                    """,
                    {"now": datetime.now(), "room": int(room_id)},
                )
                log_action(user["username"], f"Check-out booking #{selected_id}")
                st.success("Check-out thành công. Phòng đã chuyển sang 'Cần dọn'.")
                st.rerun()


# =========================================================
# GUEST MANAGEMENT
# =========================================================
elif page == "👥 Quản lý khách":
    st.title("👥 Quản lý thông tin khách")

    tab1, tab2 = st.tabs(["➕ Thêm khách", "📋 Hồ sơ khách"])

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
                sql(
                    """
                    INSERT INTO guests
                    (full_name, phone, email, id_number, address, note, created_at)
                    VALUES (:name, :phone, :email, :id_number, :address, :note, :created)
                    """,
                    {
                        "name": name.strip(),
                        "phone": phone,
                        "email": email,
                        "id_number": id_number,
                        "address": address,
                        "note": note,
                        "created": datetime.now(),
                    },
                )
                log_action(user["username"], f"Thêm khách {name}")
                st.success("Đã lưu hồ sơ khách.")
                st.rerun()

    with tab2:
        guest_df = read_df(
            """
            SELECT
                id AS `ID`, full_name AS `Họ tên`, phone AS `SĐT`,
                email AS `Email`, id_number AS `CCCD/Hộ chiếu`,
                address AS `Địa chỉ`, note AS `Ghi chú`
            FROM guests ORDER BY id DESC
            """
        )
        st.dataframe(guest_df, use_container_width=True, hide_index=True)


# =========================================================
# PAYMENTS
# =========================================================
elif page == "💳 Quản lý thanh toán":
    st.title("💳 Quản lý thanh toán")

    bookings = booking_data()
    active = bookings[bookings["Trạng thái"].isin(["Đã đặt", "Đã check-in"])]

    if active.empty:
        st.info("Không có booking cần thanh toán.")
    else:
        selected_id = st.selectbox("Mã đặt phòng", active["Mã đặt"].tolist())
        row = active[active["Mã đặt"] == selected_id].iloc[0]
        total = booking_total(selected_id)
        paid = float(row["Đã thanh toán"] or 0)
        remaining = max(0, total - paid)

        a, b, c = st.columns(3)
        a.metric("Tổng tiền", money(total))
        b.metric("Đã trả", money(paid))
        c.metric("Còn lại", money(remaining))

        amount = st.number_input(
            "Số tiền thanh toán",
            min_value=0.0,
            max_value=float(remaining),
            value=float(remaining),
            step=50000.0,
        )
        method = st.selectbox("Phương thức", PAYMENT_METHODS)
        payment_type = st.selectbox("Loại giao dịch", ["Đặt cọc", "Thanh toán", "Hoàn tiền"])
        note = st.text_input("Ghi chú")

        if st.button("💰 Ghi nhận giao dịch", use_container_width=True):
            if amount <= 0:
                st.error("Số tiền phải lớn hơn 0.")
            else:
                sql(
                    """
                    INSERT INTO payments
                    (booking_id, amount, method, payment_type, paid_at, note)
                    VALUES (:booking, :amount, :method, :type, :paid, :note)
                    """,
                    {
                        "booking": int(selected_id),
                        "amount": amount,
                        "method": method,
                        "type": payment_type,
                        "paid": datetime.now(),
                        "note": note,
                    },
                )
                log_action(user["username"], f"Thu {money(amount)} booking #{selected_id}")
                st.success("Đã ghi nhận thanh toán.")
                st.rerun()

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

    df = room_data()
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    selected_room = st.selectbox("Chọn phòng", df["Phòng"].tolist())
    current = df[df["Phòng"] == selected_room].iloc[0]

    status = st.selectbox(
        "Trạng thái vệ sinh",
        HOUSE_STATUSES,
        index=HOUSE_STATUSES.index(current["Housekeeping"])
        if current["Housekeeping"] in HOUSE_STATUSES else 0,
    )
    staff = st.text_input("Nhân viên phụ trách", value=current["Nhân viên dọn"])
    note = st.text_input("Ghi chú")

    if st.button("💾 Cập nhật Housekeeping", use_container_width=True):
        room_id = int(current["room_id"])
        sql(
            """
            UPDATE housekeeping
            SET status=:status, staff=:staff, updated_at=:now, note=:note
            WHERE room_id=:room
            """,
            {
                "status": status,
                "staff": staff,
                "now": datetime.now(),
                "note": note,
                "room": room_id,
            },
        )
        log_action(user["username"], f"Housekeeping phòng {selected_room}: {status}")
        st.success("Đã cập nhật trạng thái phòng.")
        st.rerun()


# =========================================================
# MAINTENANCE
# =========================================================
elif page == "🔧 Bảo trì":
    st.title("🔧 Quản lý bảo trì")

    tab1, tab2 = st.tabs(["➕ Tạo phiếu bảo trì", "📋 Theo dõi"])

    with tab1:
        rooms = read_df("SELECT id, room_number FROM rooms ORDER BY room_number")
        with st.form("maintenance_form"):
            room_label = st.selectbox(
                "Phòng",
                ["Toàn khách sạn"]
                + [f"P.{r['room_number']}" for _, r in rooms.iterrows()],
            )
            title = st.text_input("Tiêu đề lỗi")
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
                    room_id = int(
                        rooms[rooms["room_number"].eq(number)].iloc[0]["id"]
                    )
                sql(
                    """
                    INSERT INTO maintenance
                    (room_id, title, description, priority, status,
                     assigned_to, created_at)
                    VALUES (:room, :title, :description, :priority, 'Mới',
                            :assigned, :created)
                    """,
                    {
                        "room": room_id,
                        "title": title,
                        "description": description,
                        "priority": priority,
                        "assigned": assigned,
                        "created": datetime.now(),
                    },
                )
                if room_id:
                    sql(
                        "UPDATE rooms SET status='Bảo trì' WHERE id=:id",
                        {"id": room_id},
                    )
                log_action(user["username"], f"Tạo phiếu bảo trì: {title}")
                st.success("Đã tạo phiếu bảo trì.")
                st.rerun()

    with tab2:
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
                sql(
                    """
                    UPDATE maintenance
                    SET status=:status,
                        completed_at=:completed
                    WHERE id=:id
                    """,
                    {
                        "status": new_status,
                        "completed": datetime.now()
                        if new_status == "Hoàn thành"
                        else None,
                        "id": int(ticket),
                    },
                )

                row = maintenance[maintenance["ID"] == ticket].iloc[0]
                room_text = row["Phòng"]
                if room_text != "Toàn khách sạn" and new_status == "Hoàn thành":
                    number = str(room_text).replace("P.", "")
                    sql(
                        "UPDATE rooms SET status='Trống' WHERE room_number=:room",
                        {"room": number},
                    )
                log_action(user["username"], f"Cập nhật phiếu bảo trì #{ticket}")
                st.success("Đã cập nhật.")
                st.rerun()


# =========================================================
# REVENUE REPORT
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
        payments["Doanh thu"] = pd.to_numeric(payments["Doanh thu"])

        start = st.date_input("Từ ngày", value=date.today() - timedelta(days=30))
        end = st.date_input("Đến ngày", value=date.today())

        filtered = payments[
            (payments["Ngày"].dt.date >= start)
            & (payments["Ngày"].dt.date <= end)
        ]

        revenue = filtered["Doanh thu"].sum()
        transactions = len(filtered)

        a, b = st.columns(2)
        a.metric("💰 Tổng doanh thu", money(revenue))
        b.metric("🧾 Số giao dịch", transactions)

        daily = (
            filtered.groupby(filtered["Ngày"].dt.date)["Doanh thu"]
            .sum()
            .reset_index()
        )
        daily.columns = ["Ngày", "Doanh thu"]
        st.subheader("📈 Doanh thu theo ngày")
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
        value=date.today() - timedelta(days=30),
        key="occ_start",
    )
    end = st.date_input(
        "Ngày kết thúc",
        value=date.today(),
        key="occ_end",
    )

    if end < start:
        st.error("Khoảng ngày không hợp lệ.")
    else:
        days = (end - start).days + 1
        booked_nights = read_df(
            """
            SELECT COALESCE(SUM(
                DATEDIFF(
                    LEAST(check_out, :end_plus),
                    GREATEST(check_in, :start)
                )
            ), 0) AS nights
            FROM bookings
            WHERE status <> 'Đã hủy'
              AND check_in < :end_plus
              AND check_out > :start
            """,
            {
                "start": start,
                "end_plus": end + timedelta(days=1),
            },
        ).iloc[0]["nights"]

        capacity = total_rooms * days
        occupancy = (float(booked_nights) / capacity * 100) if capacity else 0

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
                COALESCE(SUM(
                    DATEDIFF(
                        LEAST(b.check_out, :end_plus),
                        GREATEST(b.check_in, :start)
                    )
                ), 0) AS `Đêm đã bán`
            FROM rooms r
            LEFT JOIN bookings b
              ON b.room_id=r.id
             AND b.status <> 'Đã hủy'
             AND b.check_in < :end_plus
             AND b.check_out > :start
            GROUP BY r.room_type
            ORDER BY r.room_type
            """,
            {
                "start": start,
                "end_plus": end + timedelta(days=1),
            },
        )
        st.subheader("🏨 Công suất theo hạng phòng")
        st.dataframe(by_type, use_container_width=True, hide_index=True)


# =========================================================
# EMPLOYEE / ROLE MANAGEMENT
# =========================================================
elif page == "👨‍💼 Phân quyền nhân viên":
    st.title("👨‍💼 Phân quyền nhân viên")
    st.caption("Chỉ Quản trị viên được truy cập chức năng này.")

    employees = read_df(
        """
        SELECT
            id AS `ID`, full_name AS `Họ tên`, username AS `Tài khoản`,
            role AS `Vai trò`, phone AS `SĐT`, active AS `Đang hoạt động`
        FROM employees ORDER BY id
        """
    )
    st.dataframe(employees, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("➕ Tạo tài khoản nhân viên")

    roles = [
        "Quản trị viên",
        "Lễ tân",
        "Housekeeping",
        "Kế toán",
        "Bảo trì",
    ]

    with st.form("employee_form"):
        full_name = st.text_input("Họ tên")
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        role = st.selectbox("Vai trò", roles)
        phone = st.text_input("Số điện thoại")
        submit = st.form_submit_button("💾 Tạo tài khoản", use_container_width=True)

    if submit:
        try:
            sql(
                """
                INSERT INTO employees
                (full_name, username, password, role, phone, active, created_at)
                VALUES (:name, :username, :password, :role, :phone, 1, :created)
                """,
                {
                    "name": full_name,
                    "username": username,
                    "password": password,
                    "role": role,
                    "phone": phone,
                    "created": datetime.now(),
                },
            )
            log_action(user["username"], f"Tạo tài khoản {username}")
            st.success("Đã tạo tài khoản.")
            st.rerun()
        except Exception as e:
            st.error("Không thể tạo tài khoản.")
            st.code(str(e))

    st.subheader("🔄 Khóa / mở tài khoản")
    if not employees.empty:
        employee_id = st.selectbox("Chọn ID nhân viên", employees["ID"].tolist())
        active_value = st.selectbox("Trạng thái", [1, 0], format_func=lambda x: "Hoạt động" if x else "Đã khóa")
        if st.button("💾 Cập nhật quyền truy cập"):
            sql(
                "UPDATE employees SET active=:active WHERE id=:id",
                {"active": int(active_value), "id": int(employee_id)},
            )
            log_action(user["username"], f"Đổi trạng thái tài khoản #{employee_id}")
            st.success("Đã cập nhật.")
            st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.sidebar.divider()
st.sidebar.caption("🏨 Hotel 4★ Management")
st.sidebar.caption("Streamlit • Python • Aiven MySQL")
