import os
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Quản Lý Khách Sạn", layout="wide")

CSV_FILE = "history_hotel.csv"

# Danh mục phòng & giá phòng theo loại (Cấu trúc tương tự menu nhà hàng)
hotel_rooms = {
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

if "booking_dict" not in st.session_state:
    st.session_state.booking_dict = {}

if "history" not in st.session_state:
    if os.path.exists(CSV_FILE):
        try:
            df_loaded = pd.read_csv(CSV_FILE)
            st.session_state.history = df_loaded.to_dict(orient="records")
        except Exception:
            st.session_state.history = []
    else:
        st.session_state.history = []

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

page = st.sidebar.radio("📋 Chọn trang hệ thống", ["🏨 Dat Phong", "🔑 Admin"])

# --- TRANG 1: ĐẶT PHÒNG / THUÊ PHÒNG ---
if page == "🏨 Dat Phong":
    st.title("🏨 Hệ Thống Quản Lý Đặt Phòng Khách Sạn")
    st.caption("Ghi nhận đặt phòng và dịch vụ thời gian thực")

    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("Chọn Phòng & Số Đêm")
        customer_name = st.text_input("👤 Tên khách hàng:", value="Khách lẻ")
        category = st.selectbox("Chọn hạng phòng:", list(hotel_rooms.keys()))
        room_name = st.selectbox("Chọn phòng:", list(hotel_rooms[category].keys()))
        nights = st.number_input("Số đêm ở:", min_value=1, step=1, value=1)

        if st.button("➕ Thêm vào phiếu đặt"):
            price = hotel_rooms[category][room_name]
            
            st.session_state.booking_dict[room_name] = {
                "Khách hàng": customer_name,
                "Tên phòng": room_name,
                "Giá / đêm": price,
                "Số đêm": nights,
                "Thành tiền": price * nights,
            }
            st.success(f"Đã thêm {room_name} vào danh sách!")
            st.rerun()

    with col2:
        st.subheader("Danh sách phòng đang chọn")

        if st.session_state.booking_dict:
            df = pd.DataFrame.from_dict(st.session_state.booking_dict, orient="index")
            st.table(df[["Khách hàng", "Tên phòng", "Giá / đêm", "Số đêm", "Thành tiền"]])

            tam_tinh = df["Thành tiền"].sum()
            giam_gia = tam_tinh * 0.10 if tam_tinh > 2000000 else 0  # Giảm 10% cho hóa đơn > 2M
            tong_thanh_toan = tam_tinh - giam_gia

            st.write(f"**Tạm tính:** {tam_tinh:,.0f} VNĐ")
            if giam_gia > 0:
              st.write(f"**Giảm giá (10% cho HĐ > 2M):** -{giam_gia:,.0f} VNĐ")
            st.metric("Tổng thanh toán", f"{tong_thanh_toan:,.0f} VNĐ")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("💳 Thanh toán & Cho thuê"):
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    for row in st.session_state.booking_dict.values():
                        st.session_state.history.append({
                            "Thời gian": now_str,
                            "Khách hàng": row["Khách hàng"],
                            "Tên phòng": row["Tên phòng"],
                            "Số đêm": row["Số đêm"],
                            "Thành tiền": row["Thành tiền"],
                        })

                    try:
                        df_history = pd.DataFrame(st.session_state.history)
                        df_history.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
                    except Exception as e:
                        st.error(f"Lỗi ghi dữ liệu xuống máy chủ: {e}")

                    st.success("Thanh toán thành công! Đã lưu lịch sử đặt phòng.")
                    st.session_state.booking_dict = {}
                    st.rerun()

            with col_btn2:
                if st.button("🗑️ Xóa toàn bộ phiếu"):
                    st.session_state.booking_dict = {}
                    st.rerun()
        else:
            st.info("Chưa có phòng nào được chọn. Hãy chọn thông tin bên trái.")

# --- TRANG 2: ADMIN & BÁO CÁO DOANH THU ---
elif page == "🔑 Admin":
    st.title("🔑 Trang Quản Trị & Doanh Thu Khách Sạn")

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

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.success("Đã xác thực quyền Quản trị viên thành công!")
    with col_btn:
        if st.button("🔒 Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()

    tab1, tab2 = st.tabs(["📋 Bảng Giá Phòng", "💰 Doanh Thu & Lịch Sử"])

    with tab1:
        st.subheader("Bảng giá các hạng phòng")
        data = []
        for cat in hotel_rooms:
            for room, price in hotel_rooms[cat].items():
                data.append([cat, room, price])
        df_rooms = pd.DataFrame(data, columns=["Hạng phòng", "Tên phòng", "Đơn giá / Đêm (VNĐ)"])
      st.dataframe(df_rooms, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Lịch sử giao dịch & Doanh thu")
        if os.path.exists(CSV_FILE):
            try:
                df_history = pd.read_csv(CSV_FILE)
            except Exception:
                df_history = pd.DataFrame()
        else:
            df_history = pd.DataFrame()

        if not df_history.empty:
            tong_doanh_thu = df_history["Thành tiền"].sum()
            st.metric("Tổng doanh thu khách sạn", f"{tong_doanh_thu:,.0f} VNĐ")
            st.markdown("---")
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa ghi nhận giao dịch nào.")
