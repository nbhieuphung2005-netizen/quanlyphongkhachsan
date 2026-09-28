import os
from datetime import datetime
import pandas as pd
import streamlit as st
st.image("VT.jpg")
# ---------------------------------------------------------
# CẤU HÌNH TRANG WEB STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ Thống Quản Lý Khách Sạn",
    page_icon="🏨",
    layout="wide"
)

# Đường dẫn file dữ liệu lưu trữ cố định
CSV_BOOKING = "booking_history.csv"
CSV_CLEANING = "cleaning_history.csv"

# Danh mục danh sách phòng & Bảng giá cố định
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

STATUS_OPTIONS = ["Trống - Sạch", "Đang ở", "Cần dọn", "Đang dọn", "Bảo trì"]
STAFF_LIST = ["Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Chưa phân công"]

# ---------------------------------------------------------
# KHỞI TẠO DỮ LIỆU BỘ NHỚ (SESSION STATE)
# ---------------------------------------------------------
if "booking_dict" not in st.session_state:
    st.session_state.booking_dict = {}

# Tải lịch sử đặt phòng
if "booking_history" not in st.session_state:
    if os.path.exists(CSV_BOOKING):
        try:
            df_b = pd.read_csv(CSV_BOOKING)
            st.session_state.booking_history = df_b.to_dict(orient="records")
        except Exception:
            st.session_state.booking_history = []
    else:
        st.session_state.booking_history = []

# Tải trạng thái dọn phòng
if "cleaning_status" not in st.session_state:
    # Khởi tạo danh sách phòng mặc định
    default_data = []
    for cat, rooms in HOTEL_ROOMS.items():
        for room_name in rooms.keys():
            default_data.append({
                "Phòng": room_name,
                "Hạng phòng": cat,
                "Trạng thái": "Trống - Sạch",
                "Nhân viên": "Chưa phân công",
                "Cập nhật cuối": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
    st.session_state.cleaning_status = pd.DataFrame(default_data)

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ---------------------------------------------------------
# THANH ĐIỀU HƯỚNG SIDEBAR
# ---------------------------------------------------------
page = st.sidebar.radio(
    "📋 Chọn trang hệ thống", 
    ["🛎️ Đặt & Thường Trực", "🧹 Theo Dõi Dọn Phòng", "🔑 Admin & Báo Cáo"]
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
        customer_name = st.text_input("👤 Tên khách hàng:", value="Khách lẻ")
        category = st.selectbox("Chọn hạng phòng:", list(HOTEL_ROOMS.keys()))
        room_name = st.selectbox("Chọn phòng:", list(HOTEL_ROOMS[category].keys()))
        nights = st.number_input("Số đêm ở:", min_value=1, step=1, value=1)

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
            df_temp = pd.DataFrame.from_dict(st.session_state.booking_dict, orient="index")
            st.table(df_temp[["Khách hàng", "Tên phòng", "Giá / đêm", "Số đêm", "Thành tiền"]])

            tam_tinh = df_temp["Thành tiền"].sum()
            giam_gia = tam_tinh * 0.10 if tam_tinh >= 2000000 else 0
            tong_thanh_toan = tam_tinh - giam_gia

            st.write(f"**Tạm tính:** {tam_tinh:,.0f} VNĐ")
            if giam_gia > 0:
                st.write(f"**Giảm giá (10% cho HĐ >= 2M):** -{giam_gia:,.0f} VNĐ")
            st.metric("Tổng thanh toán thực tế", f"{tong_thanh_toan:,.0f} VNĐ")

            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.button("💳 Thanh toán & Nhận phòng"):
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    for row in st.session_state.booking_dict.values():
                        st.session_state.booking_history.append({
                            "Thời gian": now_str,
                            "Khách hàng": row["Khách hàng"],
                            "Tên phòng": row["Tên phòng"],
                            "Số đêm": row["Số đêm"],
                            "Thành tiền": row["Thành tiền"],
                        })
                        
                        # Cập nhật tự động trạng thái dọn phòng sang "Đang ở"
                        df_c = st.session_state.cleaning_status
                        idx = df_c[df_c["Phòng"] == row["Tên phòng"]].index
                        if not idx.empty:
                            st.session_state.cleaning_status.at[idx[0], "Trạng thái"] = "Đang ở"

                    # Lưu file CSV
                    try:
                        df_hist = pd.DataFrame(st.session_state.booking_history)
                        df_hist.to_csv(CSV_BOOKING, index=False, encoding="utf-8-sig")
                    except Exception as e:
                        st.error(f"Lỗi ghi dữ liệu xuống máy chủ: {e}")

                    st.success("Thanh toán thành công! Dữ liệu đã được lưu trữ.")
                    st.session_state.booking_dict = {}
                    st.rerun()

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

    df_clean = st.session_state.cleaning_status

    # Chỉ số nhanh
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 Sạch sẵn sàng", len(df_clean[df_clean["Trạng thái"] == "Trống - Sạch"]))
    m2.metric("🧹 Cần dọn", len(df_clean[df_clean["Trạng thái"] == "Cần dọn"]))
    m3.metric("⏳ Đang dọn", len(df_clean[df_clean["Trạng thái"] == "Đang dọn"]))
    m4.metric("🔴 Đang có khách", len(df_clean[df_clean["Trạng thái"] == "Đang ở"]))

    st.markdown("---")
    col_update, col_view = st.columns([1, 1.3])

    with col_update:
        st.subheader("Cập nhật trạng thái")
        selected_room = st.selectbox("🛏️ Chọn phòng:", df_clean["Phòng"].tolist())
        
        current_row = df_clean[df_clean["Phòng"] == selected_room].iloc[0]
        st.info(f"Hiện tại: **{current_row['Trạng thái']}** | NV: **{current_row['Nhân viên']}**")

        new_status = st.selectbox(
            "🔄 Trạng thái mới:", 
            STATUS_OPTIONS, 
            index=STATUS_OPTIONS.index(current_row["Trạng thái"])
        )
        assigned_staff = st.selectbox(
            "👤 Nhân viên phụ trách:", 
            STAFF_LIST, 
            index=STAFF_LIST.index(current_row["Nhân viên"]) if current_row["Nhân viên"] in STAFF_LIST else 0
        )

        if st.button("💾 Lưu Cập Nhật"):
            idx = df_clean[df_clean["Phòng"] == selected_room].index[0]
            st.session_state.cleaning_status.at[idx, "Trạng thái"] = new_status
            st.session_state.cleaning_status.at[idx, "Nhân viên"] = assigned_staff
            st.session_state.cleaning_status.at[idx, "Cập nhật cuối"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.success(f"Đã cập nhật phòng {selected_room}!")
            st.rerun()

    with col_view:
        st.subheader("📌 Danh sách trạng thái phòng")

        def highlight_status(val):
            color_map = {
                "Trống - Sạch": "background-color: #d4edda; color: #155724;",
                "Cần dọn": "background-color: #f8d7da; color: #721c24;",
                "Đang dọn": "background-color: #fff3cd; color: #856404;",
                "Đang ở": "background-color: #cce5ff; color: #004085;",
                "Bảo trì": "background-color: #e2e3e5; color: #383d41;"
            }
            return color_map.get(val, "")

        # Sử dụng .map() để tránh lỗi Indentation / Deprecation trên Pandas mới
        st.dataframe(
            df_clean.style.map(highlight_status, subset=["Trạng thái"]),
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
            password = st.text_input("Nhập mật khẩu quản trị", type="password")
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
            st.session_state
