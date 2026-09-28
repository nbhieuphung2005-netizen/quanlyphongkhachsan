import os
from datetime import datetime, date, timedelta

import pandas as pd
import pymysql
import streamlit as st
from sqlalchemy import create_engine, text


# =========================================================
# CẤU HÌNH WEBSITE
# =========================================================

st.set_page_config(
    page_title="Hotel 4★ Management",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CẤU HÌNH AIVEN MYSQL
# =========================================================
#
# QUAN TRỌNG:
# - Host: copy chính xác từ Aiven
# - Port: theo thông tin bạn gửi là 14483
# - User: avnadmin
# - Database: hotel_management
#
# Không ghi password trực tiếp vào code.
# App sẽ cho nhập password Aiven ở màn hình kết nối.
#
# =========================================================

DB_HOST = os.getenv(
    "AIVEN_HOST",
    "mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com"
)

DB_PORT = int(
    os.getenv("AIVEN_PORT", "18185")
)

DB_USER = os.getenv(
    "AIVEN_USER",
    "avnadmin"
)

DB_NAME = os.getenv(
    "AIVEN_DATABASE",
    "defaultdb"
)


# =========================================================
# NHẬP PASSWORD AIVEN
# =========================================================

if "db_password" not in st.session_state:
    st.session_state.db_password = ""


if not st.session_state.db_password:

    st.title("🏨 HOTEL 4★ MANAGEMENT")

    st.info(
        """
        ### 🔐 Kết nối Aiven MySQL

        Vui lòng nhập **Password hiện tại của Aiven**.

        Thông tin kết nối:

        - Host: mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com
        - Port: 18185
        - User: avnadmin
        - Password: AVNS_rj_gp0uGmWQZNzuobwe
        - Database: defaultdb
        """
    )

    with st.form("database_login"):

        password = st.text_input(
            "🔑 Password Aiven",
            type="password"
        )

        connect_button = st.form_submit_button(
            "🔌 Kết nối cơ sở dữ liệu",
            use_container_width=True
        )

    if connect_button:

        if not password.strip():

            st.error("❌ Vui lòng nhập Password Aiven.")

        else:

            st.session_state.db_password = password.strip()

            st.rerun()

    st.stop()


DB_PASSWORD = st.session_state.db_password


# =========================================================
# KẾT NỐI AIVEN
# =========================================================

@st.cache_resource
def get_database(
    host,
    port,
    user,
    password,
    database
):

    def connect_without_database():

        return pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
            autocommit=True,
            ssl={},
            connect_timeout=20,
        )

    # -----------------------------------------------------
    # Kết nối server trước, chưa chọn database
    # -----------------------------------------------------

    connection = connect_without_database()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                CREATE DATABASE IF NOT EXISTS `{database}`
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )

    finally:

        connection.close()


    # -----------------------------------------------------
    # Kết nối database
    # -----------------------------------------------------

    def connect():

        return pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            autocommit=True,
            ssl={},
            connect_timeout=20,
        )


    # Test connection

    test_connection = connect()

    test_connection.close()


    # SQLAlchemy engine

    engine = create_engine(
        "mysql+pymysql://",
        creator=connect,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

    return engine


# =========================================================
# KẾT NỐI
# =========================================================

try:

    DB = get_database(
        DB_HOST,
        DB_PORT,
        DB_USER,
        DB_PASSWORD,
        DB_NAME
    )

except Exception as e:

    st.error("❌ Không thể kết nối MySQL Aiven.")

    error_text = str(e)

    st.code(error_text)

    if "1045" in error_text:

        st.warning(
            """
            🔴 **Lỗi 1045 - Access denied**

            Aiven đã nhận được kết nối nhưng tài khoản/password
            không được chấp nhận.

            Hãy kiểm tra:

            1. User phải là `avnadmin`
            2. Password phải là password hiện tại của Aiven
            3. Nếu bạn đã gửi password ở nơi khác, hãy tạo password mới.
            """
        )

    elif "2003" in error_text:

        st.warning(
            """
            🔴 **Lỗi 2003 - Không kết nối được server**

            Hãy kiểm tra lại:

            - DB_HOST
            - DB_PORT
            - Aiven service còn Running hay không
            """
        )

    elif "1049" in error_text:

        st.warning(
            """
            🔴 **Lỗi 1049 - Database không tồn tại**

            App này đã được viết để tự tạo:

            `hotel_management`

            Nếu vẫn gặp lỗi này, kiểm tra quyền của tài khoản
            `avnadmin` trên Aiven.
            """
        )

    if st.button("🔄 Nhập lại password"):

        st.session_state.db_password = ""

        st.rerun()

    st.stop()


# =========================================================
# HÀM SQL
# =========================================================

def execute_sql(query, params=None):

    with DB.begin() as connection:

        return connection.execute(
            text(query),
            params or {}
        )


def read_sql(query, params=None):

    with DB.connect() as connection:

        return pd.read_sql(
            text(query),
            connection,
            params=params or {}
        )


# =========================================================
# KIỂM TRA DATABASE
# =========================================================

try:

    current_database = read_sql(
        "SELECT DATABASE() AS db"
    ).iloc[0]["db"]

except Exception as e:

    st.error("❌ Không kiểm tra được database.")

    st.code(str(e))

    st.stop()


# =========================================================
# TẠO DATABASE TABLES
# =========================================================

def create_tables():

    tables = [

        # -------------------------------------------------
        # NHÂN VIÊN
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS employees (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            full_name VARCHAR(150) NOT NULL,

            username VARCHAR(80) NOT NULL UNIQUE,

            password VARCHAR(255) NOT NULL,

            role VARCHAR(60) NOT NULL,

            phone VARCHAR(30),

            active TINYINT(1) DEFAULT 1,

            created_at DATETIME NOT NULL

        )
        """,

        # -------------------------------------------------
        # KHÁCH HÀNG
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PHÒNG
        # -------------------------------------------------

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

        # -------------------------------------------------
        # ĐẶT PHÒNG
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS bookings (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            guest_id BIGINT NOT NULL,

            room_id BIGINT NOT NULL,

            check_in DATE NOT NULL,

            check_out DATE NOT NULL,

            adults INT DEFAULT 1,

            children INT DEFAULT 0,

            status VARCHAR(50) DEFAULT 'Đã đặt',

            source VARCHAR(50) DEFAULT 'Tại quầy',

            note TEXT,

            created_at DATETIME NOT NULL,

            FOREIGN KEY (guest_id)
                REFERENCES guests(id),

            FOREIGN KEY (room_id)
                REFERENCES rooms(id)

        )
        """,

        # -------------------------------------------------
        # THANH TOÁN
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS payments (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            booking_id BIGINT NOT NULL,

            amount DECIMAL(15,2) NOT NULL,

            method VARCHAR(50) NOT NULL,

            payment_type VARCHAR(50) DEFAULT 'Thanh toán',

            paid_at DATETIME NOT NULL,

            note VARCHAR(255),

            FOREIGN KEY (booking_id)
                REFERENCES bookings(id)

        )
        """,

        # -------------------------------------------------
        # HOUSEKEEPING
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS housekeeping (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            room_id BIGINT NOT NULL UNIQUE,

            status VARCHAR(50) DEFAULT 'Sạch',

            staff VARCHAR(120) DEFAULT 'Chưa phân công',

            updated_at DATETIME NOT NULL,

            note VARCHAR(255),

            FOREIGN KEY (room_id)
                REFERENCES rooms(id)

        )
        """,

        # -------------------------------------------------
        # BẢO TRÌ
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS maintenance (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            room_id BIGINT NULL,

            title VARCHAR(180) NOT NULL,

            description TEXT,

            priority VARCHAR(30) DEFAULT 'Trung bình',

            status VARCHAR(50) DEFAULT 'Mới',

            assigned_to VARCHAR(120) DEFAULT 'Chưa phân công',

            created_at DATETIME NOT NULL,

            completed_at DATETIME NULL,

            FOREIGN KEY (room_id)
                REFERENCES rooms(id)

        )
        """,

        # -------------------------------------------------
        # NHẬT KÝ HOẠT ĐỘNG
        # -------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS audit_logs (

            id BIGINT AUTO_INCREMENT PRIMARY KEY,

            username VARCHAR(80),

            action VARCHAR(255) NOT NULL,

            created_at DATETIME NOT NULL

        )
        """

    ]


    with DB.begin() as connection:

        for table in tables:

            connection.execute(
                text(table)
            )


# =========================================================
# DỮ LIỆU MẶC ĐỊNH
# =========================================================

def seed_data():

    # -----------------------------------------------------
    # NHÂN VIÊN
    # -----------------------------------------------------

    employee_count = int(
        read_sql(
            "SELECT COUNT(*) AS n FROM employees"
        ).iloc[0]["n"]
    )


    if employee_count == 0:

        employees = [

            (
                "Quản trị viên",
                "admin",
                "123456",
                "Quản trị viên",
                "0900000001"
            ),

            (
                "Lễ tân",
                "reception",
                "123456",
                "Lễ tân",
                "0900000002"
            ),

            (
                "Housekeeping",
                "housekeeping",
                "123456",
                "Housekeeping",
                "0900000003"
            ),

            (
                "Kế toán",
                "accounting",
                "123456",
                "Kế toán",
                "0900000004"
            ),

            (
                "Nhân viên bảo trì",
                "maintenance",
                "123456",
                "Bảo trì",
                "0900000005"
            )

        ]


        with DB.begin() as connection:

            for employee in employees:

                connection.execute(

                    text(
                        """
                        INSERT INTO employees
                        (
                            full_name,
                            username,
                            password,
                            role,
                            phone,
                            active,
                            created_at
                        )

                        VALUES
                        (
                            :name,
                            :username,
                            :password,
                            :role,
                            :phone,
                            1,
                            :created
                        )
                        """
                    ),

                    {
                        "name": employee[0],
                        "username": employee[1],
                        "password": employee[2],
                        "role": employee[3],
                        "phone": employee[4],
                        "created": datetime.now()
                    }

                )


    # -----------------------------------------------------
    # PHÒNG
    # -----------------------------------------------------

    room_count = int(
        read_sql(
            "SELECT COUNT(*) AS n FROM rooms"
        ).iloc[0]["n"]
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

            ("401", "President", 4, 1500000)

        ]


        with DB.begin() as connection:

            for room in rooms:

                connection.execute(

                    text(
                        """
                        INSERT INTO rooms
                        (
                            room_number,
                            room_type,
                            floor,
                            price,
                            status
                        )

                        VALUES
                        (
                            :number,
                            :type,
                            :floor,
                            :price,
                            'Trống'
                        )
                        """
                    ),

                    {
                        "number": room[0],
                        "type": room[1],
                        "floor": room[2],
                        "price": room[3]
                    }

                )


    # -----------------------------------------------------
    # HOUSEKEEPING
    # -----------------------------------------------------

    housekeeping_count = int(
        read_sql(
            "SELECT COUNT(*) AS n FROM housekeeping"
        ).iloc[0]["n"]
    )


    if housekeeping_count == 0:

        rooms = read_sql(
            "SELECT id FROM rooms"
        )


        with DB.begin() as connection:

            for room_id in rooms["id"]:

                connection.execute(

                    text(
                        """
                        INSERT INTO housekeeping
                        (
                            room_id,
                            status,
                            staff,
                            updated_at
                        )

                        VALUES
                        (
                            :room,
                            'Sạch',
                            'Chưa phân công',
                            :now
                        )
                        """
                    ),

                    {
                        "room": int(room_id),
                        "now": datetime.now()
                    }

                )


# =========================================================
# KHỞI TẠO
# =========================================================

try:

    create_tables()

    seed_data()

except Exception as e:

    st.error(
        "❌ Database kết nối được nhưng không thể tạo dữ liệu."
    )

    st.code(str(e))

    st.stop()


# =========================================================
# CONSTANTS
# =========================================================

ROOM_TYPES = [

    "Standard",

    "Deluxe",

    "VIP",

    "President"

]


ROOM_STATUSES = [

    "Trống",

    "Đã đặt",

    "Đang ở",

    "Bảo trì"

]


HOUSEKEEPING_STATUSES = [

    "Sạch",

    "Cần dọn",

    "Đang dọn",

    "Đã kiểm tra"

]


PAYMENT_METHODS = [

    "Tiền mặt",

    "Chuyển khoản",

    "Thẻ",

    "Ví điện tử"

]


BOOKING_STATUSES = [

    "Đã đặt",

    "Đã check-in",

    "Đã check-out",

    "Đã hủy"

]


PRIORITIES = [

    "Thấp",

    "Trung bình",

    "Cao",

    "Khẩn cấp"

]


MAINTENANCE_STATUSES = [

    "Mới",

    "Đang xử lý",

    "Hoàn thành",

    "Đã hủy"

]


# =========================================================
# HELPER
# =========================================================

def money(value):

    try:

        return f"{float(value or 0):,.0f} VNĐ"

    except Exception:

        return "0 VNĐ"


def log_action(username, action):

    execute_sql(

        """
        INSERT INTO audit_logs
        (
            username,
            action,
            created_at
        )

        VALUES
        (
            :username,
            :action,
            :created
        )
        """,

        {
            "username": username,
            "action": action,
            "created": datetime.now()
        }

    )


def get_employee(username, password):

    df = read_sql(

        """
        SELECT
            id,
            full_name,
            username,
            role,
            phone

        FROM employees

        WHERE username = :username

        AND password = :password

        AND active = 1

        LIMIT 1
        """,

        {
            "username": username,
            "password": password
        }

    )

    if df.empty:

        return None

    return df.iloc[0].to_dict()


def get_rooms():

    return read_sql(

        """
        SELECT

            r.id AS room_id,

            r.room_number AS `Phòng`,

            r.room_type AS `Hạng phòng`,

            r.floor AS `Tầng`,

            r.price AS `Giá/đêm`,

            r.status AS `Trạng thái`,

            COALESCE(
                h.status,
                'Sạch'
            ) AS `Housekeeping`,

            COALESCE(
                h.staff,
                'Chưa phân công'
            ) AS `Nhân viên`

        FROM rooms r

        LEFT JOIN housekeeping h

        ON h.room_id = r.id

        ORDER BY
            r.floor,
            r.room_number

        """

    )


def get_bookings():

    return read_sql(

        """
        SELECT

            b.id AS `Mã đặt`,

            g.full_name AS `Khách hàng`,

            g.phone AS `SĐT`,

            r.room_number AS `Phòng`,

            r.room_type AS `Hạng phòng`,

            b.check_in AS `Check-in`,

            b.check_out AS `Check-out`,

            DATEDIFF(
                b.check_out,
                b.check_in
            ) AS `Số đêm`,

            b.adults AS `Người lớn`,

            b.children AS `Trẻ em`,

            b.status AS `Trạng thái`,

            b.source AS `Nguồn`,

            COALESCE(
                SUM(p.amount),
                0
            ) AS `Đã thanh toán`

        FROM bookings b

        JOIN guests g
            ON g.id = b.guest_id

        JOIN rooms r
            ON r.id = b.room_id

        LEFT JOIN payments p
            ON p.booking_id = b.id

        GROUP BY

            b.id,
            g.full_name,
            g.phone,
            r.room_number,
            r.room_type,
            b.check_in,
            b.check_out,
            b.adults,
            b.children,
            b.status,
            b.source

        ORDER BY b.id DESC

        """

    )


def get_available_rooms(checkin, checkout):

    return read_sql(

        """
        SELECT r.*

        FROM rooms r

        WHERE r.status <> 'Bảo trì'

        AND NOT EXISTS (

            SELECT 1

            FROM bookings b

            WHERE b.room_id = r.id

            AND b.status IN
                ('Đã đặt', 'Đã check-in')

            AND b.check_in < :checkout

            AND b.check_out > :checkin

        )

        ORDER BY
            r.floor,
            r.room_number

        """,

        {
            "checkin": checkin,
            "checkout": checkout
        }

    )


def get_booking_total(booking_id):

    df = read_sql(

        """
        SELECT

            DATEDIFF(
                b.check_out,
                b.check_in
            ) AS nights,

            r.price

        FROM bookings b

        JOIN rooms r
            ON r.id = b.room_id

        WHERE b.id = :id

        """,

        {
            "id": int(booking_id)
        }

    )

    if df.empty:

        return 0

    nights = max(
        1,
        int(df.iloc[0]["nights"])
    )

    return (
        nights
        * float(df.iloc[0]["price"])
    )


# =========================================================
# SESSION
# =========================================================

if "user" not in st.session_state:

    st.session_state.user = None


if "page" not in st.session_state:

    st.session_state.page = "🏠 Tổng quan"


# =========================================================
# LOGIN NHÂN VIÊN
# =========================================================

if not st.session_state.user:

    st.title(
        "🏨 HOTEL 4★ MANAGEMENT"
    )

    st.caption(
        "Hệ thống quản lý khách sạn hiện đại"
    )


    left, right = st.columns(
        [1, 1.3]
    )


    with left:

        st.subheader(
            "🔐 Đăng nhập"
        )


        with st.form("login_form"):

            username = st.text_input(
                "Tên đăng nhập"
            )

            password = st.text_input(
                "Mật khẩu",
                type="password"
            )

            login = st.form_submit_button(
                "🚀 Đăng nhập",
                use_container_width=True
            )


        if login:

            account = get_employee(
                username.strip(),
                password
            )


            if account:

                st.session_state.user = account

                log_action(
                    account["username"],
                    "Đăng nhập"
                )

                st.rerun()

            else:

                st.error(
                    "❌ Sai tài khoản hoặc mật khẩu."
                )


    with right:

        st.info(
            """
            ### 👨‍💼 Tài khoản demo

            **Quản trị viên**
            `admin / 123456`

            **Lễ tân**
            `reception / 123456`

            **Housekeeping**
            `housekeeping / 123456`

            **Kế toán**
            `accounting / 123456`

            **Bảo trì**
            `maintenance / 123456`
            """
        )


    st.stop()


# =========================================================
# USER
# =========================================================

user = st.session_state.user


def has_role(*roles):

    return (
        user["role"] in roles
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "🏨 HOTEL 4★"
)

st.sidebar.success(
    f"""
👤 {user['full_name']}

🔑 {user['role']}
"""
)


st.sidebar.caption(
    f"🗄️ Database: {current_database}"
)


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

]


if has_role("Quản trị viên"):

    menus.append(
        "👨‍💼 Phân quyền nhân viên"
    )


for menu in menus:

    if st.sidebar.button(
        menu,
        use_container_width=True
    ):

        st.session_state.page = menu


if st.sidebar.button(
    "🚪 Đăng xuất",
    use_container_width=True
):

    log_action(
        user["username"],
        "Đăng xuất"
    )

    st.session_state.user = None

    st.rerun()


page = st.session_state.page


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Tổng quan":

    st.title(
        "🏨 Dashboard khách sạn 4 sao"
    )

    st.caption(
        f"Xin chào {user['full_name']} • "
        f"{datetime.now():%d/%m/%Y %H:%M}"
    )


    rooms = get_rooms()

    bookings = get_bookings()


    total_rooms = len(rooms)

    occupied = len(
        rooms[
            rooms["Trạng thái"]
            == "Đang ở"
        ]
    )

    reserved = len(
        rooms[
            rooms["Trạng thái"]
            == "Đã đặt"
        ]
    )

    clean = len(
        rooms[
            rooms["Housekeeping"]
            == "Sạch"
        ]
    )

    maintenance = len(
        rooms[
            rooms["Trạng thái"]
            == "Bảo trì"
        ]
    )


    a, b, c, d, e = st.columns(5)


    a.metric(
        "🛏️ Tổng phòng",
        total_rooms
    )

    b.metric(
        "🔴 Đang ở",
        occupied
    )

    c.metric(
        "🟡 Đã đặt",
        reserved
    )

    d.metric(
        "🟢 Sạch",
        clean
    )

    e.metric(
        "🔧 Bảo trì",
        maintenance
    )


    st.divider()


    if total_rooms:

        occupancy = (
            occupied
            / total_rooms
            * 100
        )

    else:

        occupancy = 0


    st.subheader(
        "📊 Công suất phòng hiện tại"
    )

    st.progress(
        min(
            1.0,
            occupancy / 100
        )
    )

    st.write(
        f"**{occupancy:.1f}%** "
        "phòng đang có khách."
    )


    col1, col2 = st.columns(2)


    with col1:

        st.subheader(
            "🚨 Phòng cần xử lý"
        )

        urgent = rooms[
            rooms["Housekeeping"].isin(
                [
                    "Cần dọn",
                    "Đang dọn"
                ]
            )
            |
            rooms["Trạng thái"].eq(
                "Bảo trì"
            )
        ]

        st.dataframe(
            urgent,
            use_container_width=True,
            hide_index=True
        )


    with col2:

        st.subheader(
            "🛎️ Đặt phòng gần nhất"
        )

        st.dataframe(
            bookings.head(8),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# QUẢN LÝ ĐẶT PHÒNG
# =========================================================

elif page == "🛎️ Quản lý đặt phòng":

    st.title(
        "🛎️ Quản lý đặt phòng"
    )


    tab1, tab2 = st.tabs(
        [
            "➕ Tạo đặt phòng",
            "📋 Danh sách"
        ]
    )


    with tab1:

        guests = read_sql(
            """
            SELECT
                id,
                full_name,
                phone
            FROM guests
            ORDER BY full_name
            """
        )


        if guests.empty:

            st.warning(
                "⚠️ Chưa có khách hàng. "
                "Hãy tạo khách ở mục "
                "'Quản lý khách'."
            )

        else:

            guest_map = {

                f"{r['full_name']} — "
                f"{r['phone'] or 'Không có SĐT'}":
                int(r["id"])

                for _, r
                in guests.iterrows()

            }


            guest_label = st.selectbox(
                "👤 Khách hàng",
                list(
                    guest_map.keys()
                )
            )


            checkin = st.date_input(
                "📅 Check-in",
                date.today()
            )


            checkout = st.date_input(
                "📅 Check-out",
                date.today()
                + timedelta(days=1)
            )


            adults = st.number_input(
                "👨 Người lớn",
                1,
                10,
                1
            )


            children = st.number_input(
                "👶 Trẻ em",
                0,
                10,
                0
            )


            source = st.selectbox(
                "📱 Nguồn đặt",
                [
                    "Tại quầy",
                    "Điện thoại",
                    "Website",
                    "OTA"
                ]
            )


            note = st.text_area(
                "📝 Ghi chú"
            )


            if checkout <= checkin:

                st.error(
                    "Check-out phải sau "
                    "Check-in."
                )

            else:

                available = get_available_rooms(
                    checkin,
                    checkout
                )


                if available.empty:

                    st.error(
                        "❌ Không còn phòng "
                        "trống trong khoảng "
                        "thời gian này."
                    )

                else:

                    room_labels = [

                        f"P.{r['room_number']} — "
                        f"{r['room_type']} — "
                        f"{money(r['price'])}/đêm"

                        for _, r
                        in available.iterrows()

                    ]


                    selected_room = st.selectbox(
                        "🚪 Chọn phòng",
                        room_labels
                    )


                    selected_index = (
                        room_labels.index(
                            selected_room
                        )
                    )


                    room = available.iloc[
                        selected_index
                    ]


                    nights = (
                        checkout
                        - checkin
                    ).days


                    total = (
                        nights
                        * float(
                            room["price"]
                        )
                    )


                    st.info(
                        f"""
                        🏨 Phòng: **P.{room['room_number']}**

                        🛏️ Hạng: **{room['room_type']}**

                        🌙 Số đêm: **{nights}**

                        💰 Tổng tiền: **{money(total)}**
                        """
                    )


                    if st.button(
                        "✅ Xác nhận đặt phòng",
                        use_container_width=True
                    ):

                        execute_sql(

                            """
                            INSERT INTO bookings
                            (
                                guest_id,
                                room_id,
                                check_in,
                                check_out,
                                adults,
                                children,
                                status,
                                source,
                                note,
                                created_at
                            )

                            VALUES
                            (
                                :guest,
                                :room,
                                :checkin,
                                :checkout,
                                :adults,
                                :children,
                                'Đã đặt',
                                :source,
                                :note,
                                :created
                            )
                            """,

                            {
                                "guest":
                                    guest_map[
                                        guest_label
                                    ],

                                "room":
                                    int(room["id"]),

                                "checkin":
                                    checkin,

                                "checkout":
                                    checkout,

                                "adults":
                                    int(adults),

                                "children":
                                    int(children),

                                "source":
                                    source,

                                "note":
                                    note,

                                "created":
                                    datetime.now()
                            }

                        )


                        execute_sql(

                            """
                            UPDATE rooms

                            SET status='Đã đặt'

                            WHERE id=:id
                            """,

                            {
                                "id":
                                    int(room["id"])
                            }

                        )


                        log_action(
                            user["username"],
                            f"Tạo booking phòng "
                            f"{room['room_number']}"
                        )


                        st.success(
                            "🎉 Đặt phòng thành công!"
                        )

                        st.rerun()


    with tab2:

        st.dataframe(
            get_bookings(),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# CHECK-IN / CHECK-OUT
# =========================================================

elif page == "🚪 Check-in / Check-out":

    st.title(
        "🚪 Check-in / Check-out"
    )


    bookings = get_bookings()


    active = bookings[
        bookings["Trạng thái"].isin(
            [
                "Đã đặt",
                "Đã check-in"
            ]
        )
    ]


    if active.empty:

        st.info(
            "Không có booking cần xử lý."
        )

    else:

        booking_id = st.selectbox(
            "🧾 Mã đặt phòng",
            active["Mã đặt"].tolist()
        )


        row = active[
            active["Mã đặt"]
            == booking_id
        ].iloc[0]


        a, b, c = st.columns(3)


        a.metric(
            "👤 Khách",
            row["Khách hàng"]
        )

        b.metric(
            "🚪 Phòng",
            row["Phòng"]
        )

        c.metric(
            "📌 Trạng thái",
            row["Trạng thái"]
        )


        if row["Trạng thái"] == "Đã đặt":

            if st.button(
                "🟢 CHECK-IN",
                use_container_width=True
            ):

                execute_sql(

                    """
                    UPDATE bookings

                    SET status='Đã check-in'

                    WHERE id=:id
                    """,

                    {
                        "id":
                            int(booking_id)
                    }

                )


                execute_sql(

                    """
                    UPDATE rooms

                    SET status='Đang ở'

                    WHERE room_number=:room
                    """,

                    {
                        "room":
                            row["Phòng"]
                    }

                )


                log_action(
                    user["username"],
                    f"Check-in #{booking_id}"
                )


                st.success(
                    "✅ Check-in thành công!"
                )

                st.rerun()


        elif row["Trạng thái"] == "Đã check-in":

            if st.button(
                "🔵 CHECK-OUT",
                use_container_width=True
            ):

                execute_sql(

                    """
                    UPDATE bookings

                    SET status='Đã check-out'

                    WHERE id=:id
                    """,

                    {
                        "id":
                            int(booking_id)
                    }

                )


                execute_sql(

                    """
                    UPDATE rooms

                    SET status='Trống'

                    WHERE room_number=:room
                    """,

                    {
                        "room":
                            row["Phòng"]
                    }

                )


                room_df = read_sql(

                    """
                    SELECT id
                    FROM rooms
                    WHERE room_number=:room
                    """,

                    {
                        "room":
                            row["Phòng"]
                    }

                )


                if not room_df.empty:

                    room_id = int(
                        room_df.iloc[0]["id"]
                    )


                    execute_sql(

                        """
                        UPDATE housekeeping

                        SET
                            status='Cần dọn',
                            updated_at=:now

                        WHERE room_id=:room
                        """,

                        {
                            "now":
                                datetime.now(),

                            "room":
                                room_id
                        }

                    )


                log_action(
                    user["username"],
                    f"Check-out #{booking_id}"
                )


                st.success(
                    "✅ Check-out thành công. "
                    "Phòng đã chuyển sang Cần dọn."
                )

                st.rerun()


# =========================================================
# QUẢN LÝ KHÁCH
# =========================================================

elif page == "👥 Quản lý khách":

    st.title(
        "👥 Quản lý thông tin khách"
    )


    tab1, tab2 = st.tabs(
        [
            "➕ Thêm khách",
            "📋 Danh sách khách"
        ]
    )


    with tab1:

        with st.form("guest_form"):

            name = st.text_input(
                "Họ và tên *"
            )

            phone = st.text_input(
                "Số điện thoại"
            )

            email = st.text_input(
                "Email"
            )

            id_number = st.text_input(
                "CCCD / Hộ chiếu"
            )

            address = st.text_input(
                "Địa chỉ"
            )

            note = st.text_area(
                "Ghi chú"
            )


            submit = st.form_submit_button(
                "💾 Lưu khách hàng",
                use_container_width=True
            )


        if submit:

            if not name.strip():

                st.error(
                    "Vui lòng nhập họ tên."
                )

            else:

                execute_sql(

                    """
                    INSERT INTO guests
                    (
                        full_name,
                        phone,
                        email,
                        id_number,
                        address,
                        note,
                        created_at
                    )

                    VALUES
                    (
                        :name,
                        :phone,
                        :email,
                        :id,
                        :address,
                        :note,
                        :created
                    )
                    """,

                    {
                        "name":
                            name.strip(),

                        "phone":
                            phone,

                        "email":
                            email,

                        "id":
                            id_number,

                        "address":
                            address,

                        "note":
                            note,

                        "created":
                            datetime.now()
                    }

                )


                log_action(
                    user["username"],
                    f"Thêm khách {name}"
                )


                st.success(
                    "✅ Đã lưu khách hàng."
                )

                st.rerun()


    with tab2:

        guests = read_sql(

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


        st.dataframe(
            guests,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# THANH TOÁN
# =========================================================

elif page == "💳 Quản lý thanh toán":

    st.title(
        "💳 Quản lý thanh toán"
    )


    bookings = get_bookings()


    active = bookings[
        bookings["Trạng thái"].isin(
            [
                "Đã đặt",
                "Đã check-in"
            ]
        )
    ]


    if active.empty:

        st.info(
            "Không có booking cần thanh toán."
        )

    else:

        booking_id = st.selectbox(
            "🧾 Mã đặt phòng",
            active["Mã đặt"].tolist()
        )


        row = active[
            active["Mã đặt"]
            == booking_id
        ].iloc[0]


        total = get_booking_total(
            booking_id
        )


        paid = float(
            row["Đã thanh toán"]
            or 0
        )


        remaining = max(
            0,
            total - paid
        )


        a, b, c = st.columns(3)


        a.metric(
            "💰 Tổng tiền",
            money(total)
        )


        b.metric(
            "💵 Đã trả",
            money(paid)
        )


        c.metric(
            "🧾 Còn lại",
            money(remaining)
        )


        amount = st.number_input(
            "Số tiền",
            min_value=0.0,
            max_value=float(remaining),
            value=float(remaining)
            if remaining > 0
            else 0.0,
            step=50000.0
        )


        method = st.selectbox(
            "Phương thức",
            PAYMENT_METHODS
        )


        payment_type = st.selectbox(
            "Loại giao dịch",
            [
                "Đặt cọc",
                "Thanh toán"
            ]
        )


        note = st.text_input(
            "Ghi chú"
        )


        if st.button(
            "💰 Ghi nhận thanh toán",
            use_container_width=True
        ):

            if amount <= 0:

                st.error(
                    "Số tiền phải lớn hơn 0."
                )

            else:

                execute_sql(

                    """
                    INSERT INTO payments
                    (
                        booking_id,
                        amount,
                        method,
                        payment_type,
                        paid_at,
                        note
                    )

                    VALUES
                    (
                        :booking,
                        :amount,
                        :method,
                        :type,
                        :paid,
                        :note
                    )
                    """,

                    {
                        "booking":
                            int(booking_id),

                        "amount":
                            amount,

                        "method":
                            method,

                        "type":
                            payment_type,

                        "paid":
                            datetime.now(),

                        "note":
                            note
                    }

                )


                log_action(
                    user["username"],
                    f"Thanh toán "
                    f"{money(amount)} "
                    f"booking #{booking_id}"
                )


                st.success(
                    "✅ Đã ghi nhận thanh toán."
                )

                st.rerun()


    st.divider()


    st.subheader(
        "📋 Lịch sử giao dịch"
    )


    payments = read_sql(

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

        JOIN bookings b
            ON b.id=p.booking_id

        JOIN guests g
            ON g.id=b.guest_id

        ORDER BY p.id DESC

        """

    )


    st.dataframe(
        payments,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# HOUSEKEEPING
# =========================================================

elif page == "🧹 Housekeeping":

    st.title(
        "🧹 Quản lý Housekeeping"
    )


    rooms = get_rooms()


    st.dataframe(
        rooms,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    if not rooms.empty:

        selected_room = st.selectbox(
            "🚪 Chọn phòng",
            rooms["Phòng"].tolist()
        )


        current = rooms[
            rooms["Phòng"]
            == selected_room
        ].iloc[0]


        current_status = (
            current["Housekeeping"]
        )


        status = st.selectbox(

            "Trạng thái vệ sinh",

            HOUSEKEEPING_STATUSES,

            index=(
                HOUSEKEEPING_STATUSES.index(
                    current_status
                )
                if current_status
                in HOUSEKEEPING_STATUSES
                else 0
            )

        )


        staff = st.text_input(

            "👷 Nhân viên",

            value=current["Nhân viên"]

        )


        note = st.text_input(
            "📝 Ghi chú"
        )


        if st.button(
            "💾 Cập nhật",
            use_container_width=True
        ):

            execute_sql(

                """
                UPDATE housekeeping

                SET

                    status=:status,

                    staff=:staff,

                    updated_at=:now,

                    note=:note

                WHERE room_id=:room

                """,

                {

                    "status":
                        status,

                    "staff":
                        staff,

                    "now":
                        datetime.now(),

                    "note":
                        note,

                    "room":
                        int(
                            current["room_id"]
                        )

                }

            )


            log_action(
                user["username"],
                f"Housekeeping "
                f"phòng {selected_room}"
            )


            st.success(
                "✅ Đã cập nhật phòng."
            )

            st.rerun()


# =========================================================
# BẢO TRÌ
# =========================================================

elif page == "🔧 Quản lý bảo trì":

    st.title(
        "🔧 Quản lý bảo trì"
    )


    tab1, tab2 = st.tabs(
        [
            "➕ Tạo phiếu",
            "📋 Danh sách"
        ]
    )


    with tab1:

        rooms = read_sql(
            """
            SELECT id, room_number
            FROM rooms
            ORDER BY room_number
            """
        )


        room_options = [
            "Toàn khách sạn"
        ] + [

            f"P.{r['room_number']}"

            for _, r
            in rooms.iterrows()

        ]


        with st.form(
            "maintenance_form"
        ):

            room_label = st.selectbox(
                "🚪 Phòng",
                room_options
            )


            title = st.text_input(
                "Tiêu đề lỗi *"
            )


            description = st.text_area(
                "Mô tả sự cố"
            )


            priority = st.selectbox(
                "⚠️ Mức độ",
                PRIORITIES
            )


            assigned = st.text_input(
                "👷 Nhân viên xử lý",
                "Chưa phân công"
            )


            submit = st.form_submit_button(
                "🛠️ Tạo phiếu bảo trì",
                use_container_width=True
            )


        if submit:

            if not title.strip():

                st.error(
                    "Vui lòng nhập tiêu đề."
                )

            else:

                room_id = None


                if room_label != "Toàn khách sạn":

                    number = room_label.replace(
                        "P.",
                        ""
                    )


                    found = rooms[
                        rooms["room_number"]
                        == number
                    ]


                    if not found.empty:

                        room_id = int(
                            found.iloc[0]["id"]
                        )


                execute_sql(

                    """
                    INSERT INTO maintenance
                    (
                        room_id,
                        title,
                        description,
                        priority,
                        status,
                        assigned_to,
                        created_at
                    )

                    VALUES
                    (
                        :room,
                        :title,
                        :description,
                        :priority,
                        'Mới',
                        :assigned,
                        :created
                    )
                    """,

                    {
                        "room":
                            room_id,

                        "title":
                            title,

                        "description":
                            description,

                        "priority":
                            priority,

                        "assigned":
                            assigned,

                        "created":
                            datetime.now()
                    }

                )


                if room_id:

                    execute_sql(

                        """
                        UPDATE rooms

                        SET status='Bảo trì'

                        WHERE id=:id
                        """,

                        {
                            "id":
                                room_id
                        }

                    )


                log_action(
                    user["username"],
                    f"Tạo phiếu bảo trì: {title}"
                )


                st.success(
                    "✅ Đã tạo phiếu bảo trì."
                )

                st.rerun()


    with tab2:

        maintenance = read_sql(

            """
            SELECT

                m.id AS `ID`,

                COALESCE(
                    CONCAT(
                        'P.',
                        r.room_number
                    ),
                    'Toàn khách sạn'
                ) AS `Phòng`,

                m.title AS `Tiêu đề`,

                m.description AS `Mô tả`,

                m.priority AS `Mức độ`,

                m.status AS `Trạng thái`,

                m.assigned_to AS `Nhân viên`,

                m.created_at AS `Tạo lúc`,

                m.completed_at AS `Hoàn thành`

            FROM maintenance m

            LEFT JOIN rooms r
                ON r.id=m.room_id

            ORDER BY m.id DESC

            """

        )


        st.dataframe(
            maintenance,
            use_container_width=True,
            hide_index=True
        )


        if not maintenance.empty:

            ticket = st.selectbox(
                "🧾 Phiếu",
                maintenance["ID"].tolist()
            )


            new_status = st.selectbox(
                "Trạng thái",
                MAINTENANCE_STATUSES
            )


            if st.button(
                "💾 Cập nhật phiếu"
            ):

                completed = (

                    datetime.now()

                    if new_status
                    == "Hoàn thành"

                    else None

                )


                execute_sql(

                    """
                    UPDATE maintenance

                    SET

                        status=:status,

                        completed_at=:completed

                    WHERE id=:id

                    """,

                    {

                        "status":
                            new_status,

                        "completed":
                            completed,

                        "id":
                            int(ticket)

                    }

                )


                selected_ticket = (
                    maintenance[
                        maintenance["ID"]
                        == ticket
                    ].iloc[0]
                )


                room_text = (
                    selected_ticket["Phòng"]
                )


                if (

                    room_text
                    != "Toàn khách sạn"

                    and

                    new_status
                    == "Hoàn thành"

                ):

                    room_number = (
                        str(room_text)
                        .replace("P.", "")
                    )


                    execute_sql(

                        """
                        UPDATE rooms

                        SET status='Trống'

                        WHERE room_number=:room

                        """,

                        {
                            "room":
                                room_number
                        }

                    )


                log_action(
                    user["username"],
                    f"Cập nhật bảo trì #{ticket}"
                )


                st.success(
                    "✅ Đã cập nhật phiếu."
                )

                st.rerun()


# =========================================================
# BÁO CÁO DOANH THU
# =========================================================

elif page == "📊 Báo cáo doanh thu":

    st.title(
        "📊 Báo cáo doanh thu"
    )


    payments = read_sql(

        """
        SELECT

            DATE(p.paid_at) AS `Ngày`,

            p.amount AS `Doanh thu`,

            p.method AS `Phương thức`,

            p.payment_type AS `Loại`,

            g.full_name AS `Khách`

        FROM payments p

        JOIN bookings b
            ON b.id=p.booking_id

        JOIN guests g
            ON g.id=b.guest_id

        WHERE
            p.payment_type
            <> 'Hoàn tiền'

        ORDER BY p.paid_at DESC

        """

    )


    if payments.empty:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )

    else:

        payments["Ngày"] = pd.to_datetime(
            payments["Ngày"]
        )


        payments["Doanh thu"] = pd.to_numeric(
            payments["Doanh thu"],
            errors="coerce"
        ).fillna(0)


        start = st.date_input(
            "Từ ngày",
            date.today()
            - timedelta(days=30)
        )


        end = st.date_input(
            "Đến ngày",
            date.today()
        )


        filtered = payments[
            (
                payments["Ngày"].dt.date
                >= start
            )
            &
            (
                payments["Ngày"].dt.date
                <= end
            )
        ]


        revenue = filtered[
            "Doanh thu"
        ].sum()


        transactions = len(
            filtered
        )


        a, b = st.columns(2)


        a.metric(
            "💰 Tổng doanh thu",
            money(revenue)
        )


        b.metric(
            "🧾 Giao dịch",
            transactions
        )


        daily = (

            filtered

            .groupby(
                filtered[
                    "Ngày"
                ].dt.date
            )["Doanh thu"]

            .sum()

            .reset_index()

        )


        daily.columns = [
            "Ngày",
            "Doanh thu"
        ]


        st.subheader(
            "📈 Doanh thu theo ngày"
        )


        if not daily.empty:

            st.line_chart(
                daily.set_index(
                    "Ngày"
                )
            )


        st.subheader(
            "💳 Doanh thu theo phương thức"
        )


        method_df = (

            filtered

            .groupby(
                "Phương thức"
            )["Doanh thu"]

            .sum()

            .reset_index()

        )


        st.dataframe(
            method_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# CÔNG SUẤT PHÒNG
# =========================================================

elif page == "📈 Công suất phòng":

    st.title(
        "📈 Thống kê công suất phòng"
    )


    rooms = read_sql(
        """
        SELECT
            id,
            room_number,
            room_type,
            price
        FROM rooms
        """
    )


    total_rooms = len(
        rooms
    )


    start = st.date_input(
        "📅 Ngày bắt đầu",
        date.today()
        - timedelta(days=30),
        key="occupancy_start"
    )


    end = st.date_input(
        "📅 Ngày kết thúc",
        date.today(),
        key="occupancy_end"
    )


    if end < start:

        st.error(
            "Khoảng ngày không hợp lệ."
        )

    else:

        days = (
            end - start
        ).days + 1


        booked = read_sql(

            """
            SELECT

                COALESCE(
                    SUM(
                        DATEDIFF(
                            LEAST(
                                check_out,
                                :end_plus
                            ),

                            GREATEST(
                                check_in,
                                :start
                            )
                        )
                    ),
                    0
                ) AS nights

            FROM bookings

            WHERE status <> 'Đã hủy'

            AND check_in < :end_plus

            AND check_out > :start

            """,

            {

                "start":
                    start,

                "end_plus":
                    end
                    + timedelta(days=1)

            }

        ).iloc[0]["nights"]


        capacity = (
            total_rooms
            * days
        )


        occupancy = (

            float(booked)
            / capacity
            * 100

            if capacity
            else 0

        )


        a, b, c = st.columns(3)


        a.metric(
            "🛏️ Tổng phòng",
            total_rooms
        )


        b.metric(
            "📅 Số ngày",
            days
        )


        c.metric(
            "📊 Công suất",
            f"{occupancy:.1f}%"
        )


        st.progress(
            min(
                1,
                occupancy / 100
            )
        )


        by_type = read_sql(

            """
            SELECT

                r.room_type AS `Hạng phòng`,

                COUNT(
                    DISTINCT r.id
                ) AS `Số phòng`,

                COALESCE(
                    SUM(
                        DATEDIFF(
                            LEAST(
                                b.check_out,
                                :end_plus
                            ),

                            GREATEST(
                                b.check_in,
                                :start
                            )
                        )
                    ),
                    0
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

            {

                "start":
                    start,

                "end_plus":
                    end
                    + timedelta(days=1)

            }

        )


        st.subheader(
            "🏨 Công suất theo hạng phòng"
        )


        st.dataframe(
            by_type,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# PHÂN QUYỀN NHÂN VIÊN
# =========================================================

elif page == "👨‍💼 Phân quyền nhân viên":

    if not has_role(
        "Quản trị viên"
    ):

        st.error(
            "⛔ Bạn không có quyền truy cập."
        )

        st.stop()


    st.title(
        "👨‍💼 Phân quyền nhân viên"
    )


    employees = read_sql(

        """
        SELECT

            id AS `ID`,

            full_name AS `Họ tên`,

            username AS `Tài khoản`,

            role AS `Vai trò`,

            phone AS `SĐT`,

            active AS `Hoạt động`

        FROM employees

        ORDER BY id

        """

    )


    st.dataframe(
        employees,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    st.subheader(
        "➕ Tạo tài khoản nhân viên"
    )


    roles = [

        "Quản trị viên",

        "Lễ tân",

        "Housekeeping",

        "Kế toán",

        "Bảo trì"

    ]


    with st.form(
        "employee_form"
    ):

        full_name = st.text_input(
            "Họ tên"
        )


        username = st.text_input(
            "Tên đăng nhập"
        )


        password = st.text_input(
            "Mật khẩu",
            type="password"
        )


        role = st.selectbox(
            "Vai trò",
            roles
        )


        phone = st.text_input(
            "Số điện thoại"
        )


        submit = st.form_submit_button(
            "💾 Tạo tài khoản",
            use_container_width=True
        )


    if submit:

        if not full_name.strip():

            st.error(
                "Vui lòng nhập họ tên."
            )

        elif not username.strip():

            st.error(
                "Vui lòng nhập tên đăng nhập."
            )

        elif not password:

            st.error(
                "Vui lòng nhập mật khẩu."
            )

        else:

            try:

                execute_sql(

                    """
                    INSERT INTO employees
                    (
                        full_name,
                        username,
                        password,
                        role,
                        phone,
                        active,
                        created_at
                    )

                    VALUES
                    (
                        :name,
                        :username,
                        :password,
                        :role,
                        :phone,
                        1,
                        :created
                    )
                    """,

                    {

                        "name":
                            full_name,

                        "username":
                            username,

                        "password":
                            password,

                        "role":
                            role,

                        "phone":
                            phone,

                        "created":
                            datetime.now()

                    }

                )


                log_action(
                    user["username"],
                    f"Tạo tài khoản {username}"
                )


                st.success(
                    "✅ Đã tạo tài khoản."
                )

                st.rerun()


            except Exception as e:

                st.error(
                    "❌ Không thể tạo tài khoản."
                )

                st.code(
                    str(e)
                )


    st.divider()


    st.subheader(
        "🔒 Khóa / mở tài khoản"
    )


    if not employees.empty:

        employee_id = st.selectbox(
            "ID nhân viên",
            employees["ID"].tolist()
        )


        new_active = st.selectbox(

            "Trạng thái",

            [1, 0],

            format_func=lambda x:
                "🟢 Hoạt động"
                if x
                else "🔴 Đã khóa"

        )


        if st.button(
            "💾 Cập nhật tài khoản"
        ):

            execute_sql(

                """
                UPDATE employees

                SET active=:active

                WHERE id=:id
                """,

                {

                    "active":
                        int(new_active),

                    "id":
                        int(employee_id)

                }

            )


            log_action(
                user["username"],
                f"Cập nhật nhân viên "
                f"#{employee_id}"
            )


            st.success(
                "✅ Đã cập nhật."
            )

            st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()

st.sidebar.caption(
    "🏨 Hotel 4★ Management"
)

st.sidebar.caption(
    "Streamlit + Python + Aiven MySQL"
)
