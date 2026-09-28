import os
from datetime import datetime
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ---------------------------------------------------------
# CẤU HÌNH TRANG WEB STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ Thống Quản Lý Khách Sạn",
    page_icon="🏨",
    layout="wide"
)

# Ảnh khách sạn
if os.path.exists("123.jpg"):
    st.image("123.jpg")

# ---------------------------------------------------------
# KẾT NỐI AIVEN MYSQL
# ---------------------------------------------------------
@st.cache_resource
def get_db_engine():
    # Ưu tiên lấy từ Streamlit Secrets.
    # Nếu chưa có host/port thì dùng đúng thông tin Aiven của bạn.
    try:
        cfg = st.secrets["aiven_mysql"]
        host = cfg.get(
            "host",
            "mysql-11e928b1-nbhieuphung2005-1a49.h.aivencloud.com"
        )
        port = int(cfg.get("port", 18185))
        username = cfg.get("username", "avnadmin")
        password = cfg["password"]
        database = cfg.get("database", "defaultdb")
    except Exception:
        st.error(
            "Chưa cấu hình mật khẩu Aiven. "
            "Vào Streamlit Cloud → Settings → Secrets và thêm [aiven_mysql]."
        )
        st.stop()

    # URL.create giúp mật khẩu có ký tự đặc biệt (#, @, :, /...) vẫn hoạt động.
    db_url = URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    # Aiven đang yêu cầu SSL.
    return create_engine(
        db_url,
        connect_args={"ssl": {}},
        pool_pre_ping=True,
        pool_recycle=1800,
    )


DB = get_db_engine()

# ---------------------------------------------------------
# TẠO BẢNG MYSQL
# ---------------------------------------------------------
def init_database():
    with DB.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS booking_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                thoi_gian DATETIME NOT NULL,
                khach_hang VARCHAR(255) NOT NULL,
                ten_phong VARCHAR(255) NOT NULL,
                so_dem INT NOT NULL,
                thanh_tien DECIMAL(15,2) NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cleaning_status (
                phong VARCHAR(255) PRIMARY KEY,
                hang_phong VARCHAR(255) NOT NULL,
                trang_thai VARCHAR(100) NOT NULL,
                nhan_vien VARCHAR(255) NOT NULL,
                cap_nhat_cuoi DATETIME NOT NULL
            )
        """))


try:
    init_database()
except Exception as e:
    st.error("Không thể kết nối hoặc tạo bảng MySQL Aiven.")
    st.code(str(e))
    st.stop()

# ---------------------------------------------------------
# DANH MỤC PHÒNG & BẢNG GIÁ
# ---------------------------------------------------------
HOTEL_ROOMS = {
    "Phòng Thường": {
        "P.101 (Đơn)": 300000,
        "P.102 (Đơn)": 300000,
        "P.201 (Đôi)": 450000,
        "P.202 (Đôi)": 450000,
    },
    "Phòng VIP": {
        "P.301 (VIP Đơn)": 600000,
        "P.302 (VIP Đôi)": 800000,
        "P.401 (President)": 1500000,
    },
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

# ---------------------------------------------------------
# HÀM LÀM VIỆC VỚI MYSQL
# ---------------------------------------------------------
def load_booking_history():
    try:
        with DB.connect() as conn:
            df = pd.read_sql(
                text("""
                    SELECT
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
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Lỗi đọc lịch sử đặt phòng từ MySQL: {e}")
        return []


def create_default_cleaning_data():
    default_data = []

    for cat, rooms in HOTEL_ROOMS.items():
        for room_name in rooms.keys():
            default_data.append({
                "Phòng": room_name,
                "Hạng phòng": cat,
                "Trạng thái": "Trống - Sạch",
                "Nhân viên": "Chưa phân công",
                "Cập nhật cuối": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return pd.DataFrame(default_data)


def load_cleaning_status():
    try:
        with DB.connect() as conn:
            df = pd.read_sql(
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

        # Nếu bảng chưa có dữ liệu thì tạo dữ liệu phòng mặc định.
        if df.empty:
            df = create_default_cleaning_data()
            save_cleaning_status(df)

        return df

    except Exception as e:
        st.error(f"Lỗi đọc trạng thái phòng từ MySQL: {e}")
        return create_default_cleaning_data()


def save_cleaning_status(df):
    with DB.begin() as conn:
        # Không dùng to_sql(replace) để tránh mất cấu trúc bảng.
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO cleaning_status
                    (phong, hang_phong, trang_thai, nhan_vien, cap_nhat_cuoi)
                    VALUES
                    (:phong, :hang_phong, :trang_thai, :nhan_vien, :cap_nhat_cuoi)
                    ON DUPLICATE KEY UPDATE
                        hang_phong = VALUES(hang_phong),
                        trang_thai = VALUES(trang_thai),
                        nhan_vien = VALUES(nhan_vien),
                        cap_nhat_cuoi = VALUES(cap_nhat_cuoi)
                """),
                {
                    "phong": row["Phòng"],
                    "hang_phong": row["Hạng phòng"],
                    "trang_thai": row["Trạng thái"],
                    "nhan_vien": row["Nhân viên"],
                    "cap_nhat_cuoi": pd.to_datetime(row["Cập nhật cuối"]).to_pydatetime(),
                }
            )


def insert_booking(row, now_value):
    with DB.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO booking_history
                (thoi_gian, khach_hang, ten_phong, so_dem, thanh_tien)
                VALUES
                (:thoi_gian, :khach_hang, :ten_phong, :so_dem, :thanh_tien)
            """),
            {
                "thoi_gian": now_value,
                "khach_hang": row["Khách hàng"],
                "ten_phong": row["Tên phòng"],
                "so_dem": int(row["Số đêm"]),
                "thanh_tien": float(row["Thành tiền"]),
            }
        )

        conn.execute(
            text("""
                UPDATE cleaning_status
                SET trang_thai = 'Đang ở',
                    cap_nhat_cuoi = :cap_nhat
                WHERE phong = :phong
            """),
            {
                "cap_nhat": now_value,
                "phong": row["Tên phòng"],
            }
        )


def update_room_status(room_name, new_status, staff):
    now_value = datetime.now()

    with DB.begin() as conn:
        conn.execute(
            text("""
                UPDATE cleaning_status
                SET trang_thai = :trang_thai,
                    nhan_vien = :nhan_vien,
                    cap_nhat_cuoi = :cap_nhat
                WHERE phong = :phong
            """),
            {
                "trang_thai": new_status,
                "nhan_vien": staff,
                "cap_nhat": now_value,
                "phong": room_name,
            }
        )

# ---------------------------------------------------------
# KHỞI TẠO SESSION STATE
# ---------------------------------------------------------
if "booking_dict" not in st.session_state:
    st.session_state.booking_dict = {}

if "booking_history" not in st.session_state:
    st.session_state.booking_history = load_booking_history()

if "cleaning_status" not in st.session_state:
    st.session_state.cleaning_status = load_cleaning_status()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ---------------------------------------------------------
# THANH ĐIỀU HƯỚNG SIDEBAR
# ---------------------------------------------------------
page = st.sidebar.radio(
    "📋 Chọn trang hệ thống",
    [
        "🛎️ Đặt & Thường Trực",
        "🧹 Theo Dõi Dọn Phòng",
        "🔑 Admin & Báo Cáo"
    ]
)

# ---------------------------------------------------------
# TRANG 1: LỄ TÂN & ĐẶT PHÒNG
# ---------------------------------------------------------
if page == "🛎️ Đặt & Thường Trực":
    st.title("🛎️ Quản Lý Đặt Phòng & Lễ Tân")
    st.caption("Ghi nhận thông tin đặt phòng và dịch vụ cho khách hàng")

    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("Chọn Phòng & Khách Hàng")

        customer_name = st.text_input(
            "👤 Tên khách hàng:",
            value="Khách lẻ"
        )

        category = st.selectbox(
            "Chọn hạng phòng:",
            list(HOTEL_ROOMS.keys())
        )

        room_name = st.selectbox(
            "Chọn phòng:",
            list(HOTEL_ROOMS[category].keys())
        )

        nights = st.number_input(
            "Số đêm ở:",
            min_value=1,
            step=1,
            value=1
        )

        if st.button("➕ Thêm vào phiếu đặt"):
            price = HOTEL_ROOMS[category][room_name]

            st.session_state.booking_dict[room_name] = {
                "Khách hàng": customer_name,
                "Tên phòng": room_name,
                "Giá / đêm": price,
                "Số đêm": nights,
                "Thành tiền": price * nights,
            }

            st.success(f"Đã thêm {room_name} vào danh sách đặt!")
            st.rerun()

    with col2:
        st.subheader("Phiếu đặt phòng hiện tại")

        if st.session_state.booking_dict:
            df_temp = pd.DataFrame.from_dict(
                st.session_state.booking_dict,
                orient="index"
            )

            st.table(
                df_temp[
                    [
                        "Khách hàng",
                        "Tên phòng",
                        "Giá / đêm",
                        "Số đêm",
                        "Thành tiền"
                    ]
                ]
            )

            tam_tinh = df_temp["Thành tiền"].sum()
            giam_gia = tam_tinh * 0.10 if tam_tinh >= 2000000 else 0
            tong_thanh_toan = tam_tinh - giam_gia

            st.write(f"**Tạm tính:** {tam_tinh:,.0f} VNĐ")

            if giam_gia > 0:
                st.write(
                    f"**Giảm giá (10% cho HĐ >= 2M):** "
                    f"-{giam_gia:,.0f} VNĐ"
                )

            st.metric(
                "Tổng thanh toán thực tế",
                f"{tong_thanh_toan:,.0f} VNĐ"
            )

            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.button("💳 Thanh toán & Nhận phòng"):
                    now_value = datetime.now()

                    try:
                        for row in st.session_state.booking_dict.values():
                            insert_booking(row, now_value)

                        # Đọc lại dữ liệu từ MySQL để session luôn đồng bộ.
                        st.session_state.booking_history = load_booking_history()
                        st.session_state.cleaning_status = load_cleaning_status()
                        st.session_state.booking_dict = {}

                        st.success(
                            "Thanh toán thành công! "
                            "Dữ liệu đã được lưu vào Aiven MySQL."
                        )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Lỗi lưu dữ liệu vào Aiven MySQL: {e}")

            with btn_col2:
                if st.button("🗑️ Xóa phiếu"):
                    st.session_state.booking_dict = {}
                    st.rerun()

        else:
            st.info("Phiếu đặt phòng đang trống. Hãy chọn phòng bên trái.")

# ---------------------------------------------------------
# TRANG 2: THEO DÕI VỆ SINH PHÒNG
# ---------------------------------------------------------
elif page == "🧹 Theo Dõi Dọn Phòng":
    st.title("🧹 Theo Dõi Trạng Thái Dọn Phòng")
    st.caption("Cập nhật thời gian thực tình trạng vệ sinh buồng phòng")

    # Luôn đọc lại từ MySQL để dữ liệu mới nhất.
    st.session_state.cleaning_status = load_cleaning_status()
    df_clean = st.session_state.cleaning_status

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "🟢 Sạch sẵn sàng",
        len(df_clean[df_clean["Trạng thái"] == "Trống - Sạch"])
    )

    m2.metric(
        "🧹 Cần dọn",
        len(df_clean[df_clean["Trạng thái"] == "Cần dọn"])
    )

    m3.metric(
        "⏳ Đang dọn",
        len(df_clean[df_clean["Trạng thái"] == "Đang dọn"])
    )

    m4.metric(
        "🔴 Đang có khách",
        len(df_clean[df_clean["Trạng thái"] == "Đang ở"])
    )

    st.markdown("---")

    col_update, col_view = st.columns([1, 1.3])

    with col_update:
        st.subheader("Cập nhật trạng thái")

        selected_room = st.selectbox(
            "🛏️ Chọn phòng:",
            df_clean["Phòng"].tolist()
        )

        current_row = df_clean[
            df_clean["Phòng"] == selected_room
        ].iloc[0]

        st.info(
            f"Hiện tại: **{current_row['Trạng thái']}** | "
            f"NV: **{current_row['Nhân viên']}**"
        )

        new_status = st.selectbox(
            "🔄 Trạng thái mới:",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(current_row["Trạng thái"])
        )

        assigned_staff = st.selectbox(
            "👤 Nhân viên phụ trách:",
            STAFF_LIST,
            index=(
                STAFF_LIST.index(current_row["Nhân viên"])
                if current_row["Nhân viên"] in STAFF_LIST
                else 0
            )
        )

        if st.button("💾 Lưu Cập Nhật"):
            try:
                update_room_status(
                    selected_room,
                    new_status,
                    assigned_staff
                )

                st.session_state.cleaning_status = load_cleaning_status()

                st.success(
                    f"Đã cập nhật phòng {selected_room} "
                    "và lưu vào Aiven MySQL!"
                )

                st.rerun()

            except Exception as e:
                st.error(f"Lỗi cập nhật MySQL: {e}")

    with col_view:
        st.subheader("📌 Danh sách trạng thái phòng")

        def highlight_status(val):
            color_map = {
                "Trống - Sạch":
                    "background-color: #d4edda; color: #155724;",
                "Cần dọn":
                    "background-color: #f8d7da; color: #721c24;",
                "Đang dọn":
                    "background-color: #fff3cd; color: #856404;",
                "Đang ở":
                    "background-color: #cce5ff; color: #004085;",
                "Bảo trì":
                    "background-color: #e2e3e5; color: #383d41;"
            }
            return color_map.get(val, "")

        st.dataframe(
            df_clean.style.map(
                highlight_status,
                subset=["Trạng thái"]
            ),
            use_container_width=True,
            hide_index=True
        )

# ---------------------------------------------------------
# TRANG 3: ADMIN & BÁO CÁO DOANH THU
# ---------------------------------------------------------
elif page == "🔑 Admin & Báo Cáo":
    st.title("🔑 Trang Quản Trị & Báo Cáo Doanh Thu")

    if not st.session_state.admin_logged_in:
        with st.form("admin_login_form"):
            password = st.text_input(
                "Nhập mật khẩu quản trị",
                type="password"
            )

            if st.form_submit_button("🔑 Đăng nhập"):
                if password == "123456":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Mật khẩu không chính xác!")

        st.stop()

    col_header, col_logout = st.columns([4, 1])

    with col_header:
        st.success("Đã xác thực quyền Quản trị viên!")

    with col_logout:
        if st.button("🔒 Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()

    st.markdown("---")
    st.subheader("📊 Lịch sử đặt phòng")

    booking_df = pd.DataFrame(st.session_state.booking_history)

    if not booking_df.empty:
        st.dataframe(
            booking_df,
            use_container_width=True,
            hide_index=True
        )

        total_revenue = pd.to_numeric(
            booking_df["Thành tiền"],
            errors="coerce"
        ).fillna(0).sum()

        st.metric(
            "💰 Tổng doanh thu",
            f"{total_revenue:,.0f} VNĐ"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.metric(
                "🧾 Số lượt đặt phòng",
                len(booking_df)
            )

        with col_b:
            st.metric(
                "🛏️ Tổng số đêm",
                pd.to_numeric(
                    booking_df["Số đêm"],
                    errors="coerce"
                ).fillna(0).sum()
            )
    else:
        st.info("Chưa có dữ liệu đặt phòng.")
