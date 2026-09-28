import os
from datetime import datetime

import pandas as pd
import pymysql
import streamlit as st
from sqlalchemy import create_engine, text


# =========================================================
# CẤU HÌNH WEBSITE
# =========================================================

st.set_page_config(
    page_title="Khách sạn 4 sao",
    page_icon="🏨",
    layout="wide"
)


# =========================================================
# THÔNG TIN MYSQL AIVEN
# =========================================================
# Lấy chính xác Host và Password trong Aiven.
# User / Port / Database theo thông tin bạn đưa:
#
# User     : avnadmin
# Port     : 14483
# Database : hotel_management
#
# KHÔNG dùng defaultdb hoặc port 18185 nữa.

DB_HOST = "mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com"
DB_PORT = 18185
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_dqj0WOlOyaaUQCY-wGC"
DB_NAME = "hotel_management"


# =========================================================
# KẾT NỐI MYSQL
# =========================================================

@st.cache_resource
def get_database():

    try:

        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,

            charset="utf8mb4",

            autocommit=True,

            ssl={},

            connect_timeout=20
        )

        connection.close()

        engine = create_engine(
            "mysql+pymysql://",
            creator=lambda: pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset="utf8mb4",
                autocommit=True,
                ssl={},
                connect_timeout=20
            ),
            pool_pre_ping=True,
            pool_recycle=1800
        )

        return engine

    except Exception as e:

        st.error("❌ Không thể kết nối MySQL Aiven")

        st.code(str(e))

        st.stop()


DB = get_database()


# =========================================================
# KIỂM TRA DATABASE
# =========================================================

def check_database():

    try:

        with DB.connect() as conn:

            result = conn.execute(
                text("SELECT DATABASE()")
            )

            database_name = result.scalar()

        return database_name

    except Exception as e:

        st.error("❌ Không kiểm tra được database.")

        st.code(str(e))

        st.stop()


CURRENT_DATABASE = check_database()


# =========================================================
# TẠO BẢNG
# =========================================================

def create_tables():

    with DB.begin() as conn:

        # -----------------------------------------
        # BẢNG ĐẶT PHÒNG
        # -----------------------------------------

        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS booking_history (

                    id BIGINT AUTO_INCREMENT PRIMARY KEY,

                    thoi_gian DATETIME NOT NULL,

                    khach_hang VARCHAR(255) NOT NULL,

                    ten_phong VARCHAR(255) NOT NULL,

                    so_dem INT NOT NULL,

                    thanh_tien DECIMAL(15,2) NOT NULL

                )
            """)
        )


        # -----------------------------------------
        # BẢNG TRẠNG THÁI PHÒNG
        # -----------------------------------------

        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS cleaning_status (

                    phong VARCHAR(255) PRIMARY KEY,

                    hang_phong VARCHAR(255) NOT NULL,

                    trang_thai VARCHAR(100) NOT NULL,

                    nhan_vien VARCHAR(255) NOT NULL,

                    cap_nhat_cuoi DATETIME NOT NULL

                )
            """)
        )


try:

    create_tables()

except Exception as e:

    st.error("❌ Kết nối được MySQL nhưng không tạo được bảng.")

    st.code(str(e))

    st.stop()


# =========================================================
# THÔNG TIN KHÁCH SẠN
# =========================================================

HOTEL_ROOMS = {

    "Phòng Thường": {

        "P.101 (Đơn)": 300000,

        "P.102 (Đơn)": 300000,

        "P.201 (Đôi)": 450000,

        "P.202 (Đôi)": 450000

    },

    "Phòng VIP": {

        "P.301 (VIP Đơn)": 600000,

        "P.302 (VIP Đôi)": 800000,

        "P.401 (President)": 1500000

    }

}


STATUS_OPTIONS = [

    "Trống - Sạch",

    "Đang ở",

    "Cần dọn",

    "Đang dọn",

    "Bảo trì"

]


STAFF_LIST = [

    "Nguyễn Văn A",

    "Trần Thị B",

    "Lê Văn C",

    "Chưa phân công"

]


# =========================================================
# TẠO PHÒNG MẶC ĐỊNH
# =========================================================

def initialize_rooms():

    with DB.begin() as conn:

        for category, rooms in HOTEL_ROOMS.items():

            for room, price in rooms.items():

                conn.execute(

                    text("""
                        INSERT IGNORE INTO cleaning_status
                        (
                            phong,
                            hang_phong,
                            trang_thai,
                            nhan_vien,
                            cap_nhat_cuoi
                        )

                        VALUES
                        (
                            :phong,
                            :hang_phong,
                            'Trống - Sạch',
                            'Chưa phân công',
                            :cap_nhat
                        )
                    """),

                    {
                        "phong": room,
                        "hang_phong": category,
                        "cap_nhat": datetime.now()
                    }

                )


initialize_rooms()


# =========================================================
# ĐỌC LỊCH SỬ ĐẶT PHÒNG
# =========================================================

def get_booking_history():

    with DB.connect() as conn:

        return pd.read_sql(

            text("""
                SELECT

                    id AS `ID`,

                    thoi_gian AS `Thời gian`,

                    khach_hang AS `Khách hàng`,

                    ten_phong AS `Tên phòng`,

                    so_dem AS `Số đêm`,

                    thanh_tien AS `Thành tiền`

                FROM booking_history

                ORDER BY thoi_gian DESC, id DESC
            """),

            conn

        )


# =========================================================
# ĐỌC TRẠNG THÁI PHÒNG
# =========================================================

def get_cleaning_status():

    with DB.connect() as conn:

        return pd.read_sql(

            text("""
                SELECT

                    phong AS `Phòng`,

                    hang_phong AS `Hạng phòng`,

                    trang_thai AS `Trạng thái`,

                    nhan_vien AS `Nhân viên`,

                    cap_nhat_cuoi AS `Cập nhật cuối`

                FROM cleaning_status

                ORDER BY phong
            """),

            conn

        )


# =========================================================
# LƯU ĐẶT PHÒNG
# =========================================================

def save_booking(
    customer,
    room,
    nights,
    total
):

    now = datetime.now()

    with DB.begin() as conn:

        # Lưu hóa đơn

        conn.execute(

            text("""
                INSERT INTO booking_history
                (
                    thoi_gian,
                    khach_hang,
                    ten_phong,
                    so_dem,
                    thanh_tien
                )

                VALUES
                (
                    :time,
                    :customer,
                    :room,
                    :nights,
                    :total
                )
            """),

            {
                "time": now,
                "customer": customer,
                "room": room,
                "nights": int(nights),
                "total": float(total)
            }

        )


        # Chuyển phòng thành đang ở

        conn.execute(

            text("""
                UPDATE cleaning_status

                SET

                    trang_thai = 'Đang ở',

                    cap_nhat_cuoi = :time

                WHERE phong = :room
            """),

            {
                "time": now,
                "room": room
            }

        )


# =========================================================
# CẬP NHẬT PHÒNG
# =========================================================

def update_room(
    room,
    status,
    staff
):

    with DB.begin() as conn:

        conn.execute(

            text("""
                UPDATE cleaning_status

                SET

                    trang_thai = :status,

                    nhan_vien = :staff,

                    cap_nhat_cuoi = :time

                WHERE phong = :room
            """),

            {
                "status": status,
                "staff": staff,
                "time": datetime.now(),
                "room": room
            }

        )


# =========================================================
# SESSION
# =========================================================

if "booking" not in st.session_state:

    st.session_state.booking = {}


if "admin_login" not in st.session_state:

    st.session_state.admin_login = False


# =========================================================
# ẢNH KHÁCH SẠN
# =========================================================

if os.path.exists("123.jpg"):

    st.image(
        "123.jpg",
        use_container_width=True
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏨 KHÁCH SẠN 4 SAO")

st.sidebar.success(
    f"🟢 MySQL: {CURRENT_DATABASE}"
)


page = st.sidebar.radio(

    "📋 Chức năng",

    [

        "🛎️ Đặt phòng",

        "🧹 Quản lý phòng",

        "🔑 Admin & Doanh thu"

    ]

)


# =========================================================
# TRANG ĐẶT PHÒNG
# =========================================================

if page == "🛎️ Đặt phòng":

    st.title(
        "🛎️ Quản Lý Đặt Phòng"
    )

    st.caption(
        "Hệ thống quản lý khách sạn 4 sao"
    )


    col1, col2 = st.columns(
        [1, 1.5]
    )


    # -----------------------------------------
    # CHỌN PHÒNG
    # -----------------------------------------

    with col1:

        st.subheader(
            "👤 Thông tin khách hàng"
        )


        customer = st.text_input(

            "Tên khách hàng",

            value="Khách lẻ"

        )


        category = st.selectbox(

            "Hạng phòng",

            list(HOTEL_ROOMS.keys())

        )


        room = st.selectbox(

            "Phòng",

            list(
                HOTEL_ROOMS[category].keys()
            )

        )


        price = HOTEL_ROOMS[
            category
        ][room]


        st.info(
            f"💰 {price:,.0f} VNĐ / đêm"
        )


        nights = st.number_input(

            "Số đêm",

            min_value=1,

            value=1,

            step=1

        )


        total = price * nights


        st.write(
            f"**Thành tiền:** {total:,.0f} VNĐ"
        )


        if st.button(
            "➕ Thêm vào phiếu",
            use_container_width=True
        ):

            st.session_state.booking[room] = {

                "Khách hàng": customer,

                "Tên phòng": room,

                "Giá / đêm": price,

                "Số đêm": nights,

                "Thành tiền": total

            }

            st.success(
                f"Đã thêm {room}"
            )

            st.rerun()


    # -----------------------------------------
    # PHIẾU
    # -----------------------------------------

    with col2:

        st.subheader(
            "🧾 Phiếu đặt phòng"
        )


        if st.session_state.booking:

            df = pd.DataFrame(
                st.session_state.booking.values()
            )


            st.dataframe(

                df,

                use_container_width=True,

                hide_index=True

            )


            subtotal = df[
                "Thành tiền"
            ].sum()


            discount = (

                subtotal * 0.10

                if subtotal >= 2000000

                else 0

            )


            final_total = (
                subtotal - discount
            )


            st.write(
                f"**Tạm tính:** "
                f"{subtotal:,.0f} VNĐ"
            )


            if discount:

                st.write(
                    f"**Giảm 10%:** "
                    f"-{discount:,.0f} VNĐ"
                )


            st.metric(

                "💰 Tổng thanh toán",

                f"{final_total:,.0f} VNĐ"

            )


            col_pay, col_delete = st.columns(2)


            with col_pay:

                if st.button(

                    "💳 Thanh toán",

                    use_container_width=True

                ):

                    try:

                        for item in st.session_state.booking.values():

                            save_booking(

                                item["Khách hàng"],

                                item["Tên phòng"],

                                item["Số đêm"],

                                item["Thành tiền"]

                            )


                        st.session_state.booking = {}


                        st.success(
                            "✅ Đã lưu dữ liệu vào Aiven MySQL!"
                        )

                        st.rerun()


                    except Exception as e:

                        st.error(
                            "❌ Lỗi khi lưu dữ liệu."
                        )

                        st.code(str(e))


            with col_delete:

                if st.button(

                    "🗑️ Xóa phiếu",

                    use_container_width=True

                ):

                    st.session_state.booking = {}

                    st.rerun()


        else:

            st.info(
                "Chưa có phòng trong phiếu."
            )


# =========================================================
# TRANG QUẢN LÝ PHÒNG
# =========================================================

elif page == "🧹 Quản lý phòng":

    st.title(
        "🧹 Quản Lý Trạng Thái Phòng"
    )


    df = get_cleaning_status()


    # -----------------------------------------
    # THỐNG KÊ
    # -----------------------------------------

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(

            "🟢 Phòng sạch",

            len(
                df[
                    df["Trạng thái"]
                    == "Trống - Sạch"
                ]
            )

        )


    with c2:

        st.metric(

            "🧹 Cần dọn",

            len(
                df[
                    df["Trạng thái"]
                    == "Cần dọn"
                ]
            )

        )


    with c3:

        st.metric(

            "⏳ Đang dọn",

            len(
                df[
                    df["Trạng thái"]
                    == "Đang dọn"
                ]
            )

        )


    with c4:

        st.metric(

            "🔴 Đang ở",

            len(
                df[
                    df["Trạng thái"]
                    == "Đang ở"
                ]
            )

        )


    st.divider()


    left, right = st.columns(
        [1, 1.5]
    )


    with left:

        st.subheader(
            "🔄 Cập nhật phòng"
        )


        selected_room = st.selectbox(

            "Chọn phòng",

            df["Phòng"].tolist()

        )


        current = df[
            df["Phòng"]
            == selected_room
        ].iloc[0]


        st.info(

            f"Hiện tại: "
            f"**{current['Trạng thái']}**\n\n"
            f"Nhân viên: "
            f"**{current['Nhân viên']}**"

        )


        status = st.selectbox(

            "Trạng thái mới",

            STATUS_OPTIONS,

            index=STATUS_OPTIONS.index(
                current["Trạng thái"]
            )

        )


        staff = st.selectbox(

            "Nhân viên",

            STAFF_LIST,

            index=(

                STAFF_LIST.index(
                    current["Nhân viên"]
                )

                if current["Nhân viên"]
                in STAFF_LIST

                else 0

            )

        )


        if st.button(

            "💾 Lưu cập nhật",

            use_container_width=True

        ):

            try:

                update_room(

                    selected_room,

                    status,

                    staff

                )

                st.success(
                    "✅ Đã lưu vào Aiven MySQL!"
                )

                st.rerun()

            except Exception as e:

                st.error(
                    "❌ Không thể cập nhật phòng."
                )

                st.code(str(e))


    with right:

        st.subheader(
            "📋 Danh sách phòng"
        )


        st.dataframe(

            get_cleaning_status(),

            use_container_width=True,

            hide_index=True

        )


# =========================================================
# ADMIN
# =========================================================

elif page == "🔑 Admin & Doanh thu":

    st.title(
        "🔑 Admin & Báo Cáo Doanh Thu"
    )


    if not st.session_state.admin_login:

        password = st.text_input(

            "Mật khẩu Admin",

            type="password"

        )


        if st.button(
            "🔐 Đăng nhập"
        ):

            if password == "123456":

                st.session_state.admin_login = True

                st.rerun()

            else:

                st.error(
                    "❌ Mật khẩu không đúng."
                )


        st.stop()


    st.success(
        "🟢 Đã đăng nhập Admin"
    )


    if st.button(
        "🔒 Đăng xuất"
    ):

        st.session_state.admin_login = False

        st.rerun()


    st.divider()


    st.subheader(
        "📊 Lịch sử đặt phòng"
    )


    df_booking = get_booking_history()


    if df_booking.empty:

        st.info(
            "Chưa có lượt đặt phòng."
        )

    else:

        st.dataframe(

            df_booking,

            use_container_width=True,

            hide_index=True

        )


        revenue = pd.to_numeric(

            df_booking["Thành tiền"],

            errors="coerce"

        ).fillna(0).sum()


        nights = pd.to_numeric(

            df_booking["Số đêm"],

            errors="coerce"

        ).fillna(0).sum()


        a, b, c = st.columns(3)


        with a:

            st.metric(

                "💰 Doanh thu",

                f"{revenue:,.0f} VNĐ"

            )


        with b:

            st.metric(

                "🧾 Số lượt đặt",

                len(df_booking)

            )


        with c:

            st.metric(

                "🛏️ Tổng số đêm",

                int(nights)

            )
