import os
from datetime import datetime, date, timedelta
import hashlib
import pandas as pd
import streamlit as st
st.image("123.jpg")
# =========================================================
# KHÁCH SẠN 4 SAO - HỆ THỐNG QUẢN LÝ
# Chạy: streamlit run app.py
# =========================================================

st.set_page_config(
    page_title="🏨 Hotel 4★ Management",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- CẤU HÌNH --------------------
DATA_DIR = "hotel_data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "rooms": os.path.join(DATA_DIR, "rooms.csv"),
    "guests": os.path.join(DATA_DIR, "guests.csv"),
    "bookings": os.path.join(DATA_DIR, "bookings.csv"),
    "payments": os.path.join(DATA_DIR, "payments.csv"),
    "services": os.path.join(DATA_DIR, "services.csv"),
    "maintenance": os.path.join(DATA_DIR, "maintenance.csv"),
    "housekeeping": os.path.join(DATA_DIR, "housekeeping.csv"),
    "staff": os.path.join(DATA_DIR, "staff.csv"),
    "logs": os.path.join(DATA_DIR, "activity_logs.csv"),
}

HOTEL_NAME = "GRAND RIVER HOTEL"
HOTEL_STAR = "4★"

ROOMS = [
    ("101", "Standard Single", "Phòng Thường", 300000, 1),
    ("102", "Standard Single", "Phòng Thường", 300000, 1),
    ("201", "Superior Double", "Phòng Đôi", 450000, 2),
    ("202", "Superior Double", "Phòng Đôi", 450000, 2),
    ("301", "Deluxe Single", "Phòng VIP", 600000, 1),
    ("302", "Deluxe Double", "Phòng VIP", 800000, 2),
    ("401", "President Suite", "Suite", 1500000, 2),
]

SERVICES = [
    ("S001", "🍽️ Room Service", 150000),
    ("S002", "🧺 Giặt ủi", 80000),
    ("S003", "🚗 Đưa đón sân bay", 300000),
    ("S004", "☕ Café", 60000),
    ("S005", "🍳 Bữa sáng", 120000),
    ("S006", "💆 Spa", 350000),
]

STAFF_DEFAULT = [
    ("NV001", "Nguyễn Văn A", "Lễ tân", "reception"),
    ("NV002", "Trần Thị B", "Housekeeping", "housekeeping"),
    ("NV003", "Lê Văn C", "Bảo trì", "maintenance"),
    ("NV004", "Phạm Thị D", "Kế toán", "accountant"),
    ("ADMIN", "Quản trị viên", "General Manager", "admin"),
]

ROOM_STATUS = ["Trống - Sạch", "Đang ở", "Cần dọn", "Đang dọn", "Bảo trì", "Khoá phòng"]
BOOKING_STATUS = ["Đã đặt", "Đã check-in", "Đã check-out", "Đã huỷ"]
PAYMENT_METHODS = ["Tiền mặt", "Chuyển khoản", "Thẻ"]
MAINT_STATUS = ["Mới", "Đang xử lý", "Hoàn thành", "Đóng"]
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]


# -------------------- HÀM TIỆN ÍCH --------------------
def money(x):
    try:
        return f"{float(x):,.0f} ₫"
    except Exception:
        return "0 ₫"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id(prefix):
    return prefix + datetime.now().strftime("%Y%m%d%H%M%S") + str(len(st.session_state.get("logs", [])) % 1000)


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def save_df(key):
    st.session_state[key].to_csv(FILES[key], index=False, encoding="utf-8-sig")


def load_df(key, columns, default_rows=None):
    if os.path.exists(FILES[key]):
        try:
            df = pd.read_csv(FILES[key])
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            return df[columns]
        except Exception:
            pass
    df = pd.DataFrame(default_rows or [], columns=columns)
    df.to_csv(FILES[key], index=False, encoding="utf-8-sig")
    return df


def log_action(action, detail, user=None):
    user = user or st.session_state.get("current_user", "System")
    row = {
        "Thời gian": now_str(),
        "Nhân viên": user,
        "Hành động": action,
        "Chi tiết": detail,
    }
    st.session_state.logs = pd.concat(
        [st.session_state.logs, pd.DataFrame([row])], ignore_index=True
    )
    save_df("logs")


def can(role, allowed):
    return role in allowed or role == "admin"


# -------------------- KHỞI TẠO DỮ LIỆU --------------------
room_rows = []
for no, name, category, price, capacity in ROOMS:
    room_rows.append({
        "Phòng": no,
        "Tên phòng": name,
        "Hạng phòng": category,
        "Giá/đêm": price,
        "Sức chứa": capacity,
        "Trạng thái": "Trống - Sạch",
        "Nhân viên": "Chưa phân công",
        "Cập nhật cuối": now_str(),
    })

service_rows = [{"Mã DV": x[0], "Dịch vụ": x[1], "Đơn giá": x[2]} for x in SERVICES]
staff_rows = [
    {"Mã NV": x[0], "Họ tên": x[1], "Bộ phận": x[2], "Vai trò": x[3]}
    for x in STAFF_DEFAULT
]

room_cols = ["Phòng", "Tên phòng", "Hạng phòng", "Giá/đêm", "Sức chứa", "Trạng thái", "Nhân viên", "Cập nhật cuối"]
guest_cols = ["Mã khách", "Họ tên", "CCCD/Hộ chiếu", "Quốc tịch", "SĐT", "Email", "Địa chỉ", "Ghi chú", "Ngày tạo"]
booking_cols = [
    "Mã booking", "Mã khách", "Khách hàng", "Phòng", "Ngày đặt",
    "Check-in", "Check-out", "Số đêm", "Giá/đêm", "Tiền phòng",
    "Tiền dịch vụ", "Giảm giá", "Tiền cọc", "Tổng tiền", "Còn phải trả",
    "Phương thức", "Trạng thái", "Nhân viên", "Ghi chú"
]
payment_cols = ["Mã giao dịch", "Mã booking", "Khách hàng", "Thời gian", "Số tiền", "Phương thức", "Loại", "Nhân viên"]
service_cols = ["Mã sử dụng", "Mã booking", "Khách hàng", "Dịch vụ", "Số lượng", "Đơn giá", "Thành tiền", "Thời gian"]
maintenance_cols = ["Mã phiếu", "Phòng", "Thiết bị/Lỗi", "Mô tả", "Mức độ", "Nhân viên", "Chi phí", "Trạng thái", "Ngày tạo", "Ngày hoàn thành"]
housekeeping_cols = ["Mã nhiệm vụ", "Phòng", "Loại nhiệm vụ", "Nhân viên", "Mức ưu tiên", "Trạng thái", "Thời gian tạo", "Thời gian hoàn thành"]
staff_cols = ["Mã NV", "Họ tên", "Bộ phận", "Vai trò"]
log_cols = ["Thời gian", "Nhân viên", "Hành động", "Chi tiết"]

if "rooms" not in st.session_state:
    st.session_state.rooms = load_df("rooms", room_cols, room_rows)
if "guests" not in st.session_state:
    st.session_state.guests = load_df("guests", guest_cols)
if "bookings" not in st.session_state:
    st.session_state.bookings = load_df("bookings", booking_cols)
if "payments" not in st.session_state:
    st.session_state.payments = load_df("payments", payment_cols)
if "services_used" not in st.session_state:
    st.session_state.services_used = load_df("services", service_cols)
if "maintenance" not in st.session_state:
    st.session_state.maintenance = load_df("maintenance", maintenance_cols)
if "housekeeping" not in st.session_state:
    st.session_state.housekeeping = load_df("housekeeping", housekeeping_cols)
if "staff" not in st.session_state:
    st.session_state.staff = load_df("staff", staff_cols, staff_rows)
if "logs" not in st.session_state:
    st.session_state.logs = load_df("logs", log_cols)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "current_role" not in st.session_state:
    st.session_state.current_role = ""


# -------------------- ĐĂNG NHẬP --------------------
if not st.session_state.logged_in:
    st.markdown(
        "<h1 style='text-align:center'>🏨 GRAND RIVER HOTEL</h1>"
        "<h3 style='text-align:center'>Hệ thống quản lý khách sạn 4 sao</h3>",
        unsafe_allow_html=True,
    )
    st.image("123.jpg", use_container_width=True)

    with st.form("login"):
        st.subheader("🔐 Đăng nhập hệ thống")
        username = st.text_input("Tên đăng nhập", value="ADMIN")
        password = st.text_input("Mật khẩu", type="password")
        st.caption("Tài khoản demo: ADMIN | Mật khẩu: 123456")
        submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

    if submitted:
        # Demo: ADMIN/123456. Khi triển khai thật nên đưa mật khẩu vào secrets.
        if username.upper() == "ADMIN" and password == "123456":
            st.session_state.logged_in = True
            st.session_state.current_user = "Quản trị viên"
            st.session_state.current_role = "admin"
            log_action("Đăng nhập", "Đăng nhập hệ thống")
            st.rerun()
        else:
            st.error("Tên đăng nhập hoặc mật khẩu không chính xác.")
    st.stop()


# -------------------- SIDEBAR --------------------
role = st.session_state.current_role
user = st.session_state.current_user

st.sidebar.markdown(f"# 🏨 {HOTEL_NAME}")
st.sidebar.caption(f"{HOTEL_STAR} • Hệ thống quản lý")
st.sidebar.success(f"👤 {user}")
st.sidebar.caption(f"Quyền: {role}")

pages = [
    "🏠 Dashboard",
    "🛏️ Quản lý phòng",
    "📅 Đặt phòng",
    "🛎️ Check-in / Check-out",
    "👤 Khách hàng",
    "💰 Thanh toán & Folio",
    "🧹 Housekeeping",
    "🔧 Bảo trì",
    "🍽️ Dịch vụ",
    "📊 Báo cáo & Thống kê",
    "👨‍💼 Nhân viên & Phân quyền",
    "📋 Nhật ký hoạt động",
]

page = st.sidebar.radio("📋 MENU", pages)

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    log_action("Đăng xuất", "Đăng xuất hệ thống")
    st.session_state.logged_in = False
    st.rerun()


# =========================================================
# DASHBOARD
# =========================================================
if page == "🏠 Dashboard":
    st.title("🏠 Dashboard quản lý khách sạn")
    st.caption(f"{HOTEL_NAME} • {HOTEL_STAR} • Cập nhật {now_str()}")

    rooms = st.session_state.rooms
    bookings = st.session_state.bookings
    payments = st.session_state.payments

    total_rooms = len(rooms)
    occupied = len(rooms[rooms["Trạng thái"] == "Đang ở"])
    clean = len(rooms[rooms["Trạng thái"] == "Trống - Sạch"])
    dirty = len(rooms[rooms["Trạng thái"] == "Cần dọn"])
    maintenance = len(rooms[rooms["Trạng thái"] == "Bảo trì"])
    occupancy = occupied / total_rooms * 100 if total_rooms else 0

    today = date.today().strftime("%Y-%m-%d")
    today_checkins = len(bookings[(bookings["Check-in"] == today) & (bookings["Trạng thái"] != "Đã huỷ")])
    today_checkouts = len(bookings[(bookings["Check-out"] == today) & (bookings["Trạng thái"] != "Đã huỷ")])

    revenue = pd.to_numeric(payments["Số tiền"], errors="coerce").sum() if not payments.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏨 Tổng số phòng", total_rooms)
    c2.metric("🛏️ Đang có khách", occupied)
    c3.metric("📈 Công suất phòng", f"{occupancy:.1f}%")
    c4.metric("💰 Doanh thu ghi nhận", money(revenue))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("🟢 Phòng sạch", clean)
    c6.metric("🧹 Cần dọn", dirty)
    c7.metric("🔧 Đang bảo trì", maintenance)
    c8.metric("🛎️ Check-in hôm nay", today_checkins)

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("📅 Lịch hôm nay")
        st.write(f"**Check-in:** {today_checkins} khách")
        st.write(f"**Check-out:** {today_checkouts} khách")
        st.write(f"**Phòng cần dọn:** {dirty}")
        st.write(f"**Phòng bảo trì:** {maintenance}")

    with right:
        st.subheader("🚨 Cảnh báo")
        alerts = []
        if dirty:
            alerts.append(f"🧹 Có {dirty} phòng cần dọn.")
        if maintenance:
            alerts.append(f"🔧 Có {maintenance} phòng đang bảo trì.")
        if today_checkouts:
            alerts.append(f"🛎️ Có {today_checkouts} phòng cần xử lý check-out hôm nay.")
        if not alerts:
            st.success("Không có cảnh báo quan trọng.")
        else:
            for a in alerts:
                st.warning(a)

    st.subheader("🛏️ Bản đồ trạng thái phòng")
    cols = st.columns(4)
    status_icon = {
        "Trống - Sạch": "🟢",
        "Đang ở": "🔵",
        "Cần dọn": "🟠",
        "Đang dọn": "🟡",
        "Bảo trì": "🔴",
        "Khoá phòng": "⚫",
    }
    for i, (_, row) in enumerate(rooms.iterrows()):
        with cols[i % 4]:
            st.info(
                f"{status_icon.get(row['Trạng thái'], '⚪')} **P.{row['Phòng']}**\n\n"
                f"{row['Tên phòng']}  \n{row['Trạng thái']}"
            )


# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================
elif page == "🛏️ Quản lý phòng":
    st.title("🛏️ Quản lý phòng")
    rooms = st.session_state.rooms

    f1, f2, f3 = st.columns(3)
    search = f1.text_input("🔎 Tìm phòng")
    category = f2.selectbox("Hạng phòng", ["Tất cả"] + sorted(rooms["Hạng phòng"].unique().tolist()))
    status = f3.selectbox("Trạng thái", ["Tất cả"] + ROOM_STATUS)

    view = rooms.copy()
    if search:
        view = view[view["Phòng"].astype(str).str.contains(search, case=False, na=False)]
    if category != "Tất cả":
        view = view[view["Hạng phòng"] == category]
    if status != "Tất cả":
        view = view[view["Trạng thái"] == status]

    st.dataframe(view, use_container_width=True, hide_index=True)

    if can(role, ["admin", "manager", "reception"]):
        st.markdown("---")
        st.subheader("🔄 Cập nhật trạng thái phòng")
        room_no = st.selectbox("Chọn phòng", rooms["Phòng"].tolist())
        row_idx = rooms.index[rooms["Phòng"] == room_no][0]
        new_status = st.selectbox("Trạng thái mới", ROOM_STATUS, index=ROOM_STATUS.index(rooms.at[row_idx, "Trạng thái"]))
        staff = st.selectbox("Nhân viên", ["Chưa phân công"] + st.session_state.staff["Họ tên"].tolist())

        if st.button("💾 Lưu trạng thái phòng", use_container_width=True):
            st.session_state.rooms.at[row_idx, "Trạng thái"] = new_status
            st.session_state.rooms.at[row_idx, "Nhân viên"] = staff
            st.session_state.rooms.at[row_idx, "Cập nhật cuối"] = now_str()
            save_df("rooms")
            log_action("Cập nhật phòng", f"P.{room_no} → {new_status}")
            st.success("Đã cập nhật phòng.")
            st.rerun()


# =========================================================
# ĐẶT PHÒNG
# =========================================================
elif page == "📅 Đặt phòng":
    st.title("📅 Quản lý đặt phòng")
    st.caption("Tạo booking, kiểm tra phòng và quản lý lịch lưu trú.")

    rooms = st.session_state.rooms
    guests = st.session_state.guests
    bookings = st.session_state.bookings

    with st.form("booking_form"):
        c1, c2, c3 = st.columns(3)
        guest_name = c1.text_input("👤 Họ tên khách")
        phone = c2.text_input("📱 Số điện thoại")
        nationality = c3.text_input("🌏 Quốc tịch", value="Việt Nam")

        c4, c5, c6 = st.columns(3)
        room_no = c4.selectbox(
            "🛏️ Phòng",
            rooms[rooms["Trạng thái"].isin(["Trống - Sạch", "Cần dọn"]) ]["Phòng"].tolist()
        )
        checkin = c5.date_input("📅 Check-in", value=date.today())
        checkout = c6.date_input("📅 Check-out", value=date.today() + timedelta(days=1))

        c7, c8, c9 = st.columns(3)
        deposit = c7.number_input("💵 Tiền cọc", min_value=0, step=100000)
        discount = c8.number_input("🎁 Giảm giá (%)", min_value=0.0, max_value=100.0, step=5.0)
        note = c9.text_input("📝 Ghi chú")

        submit = st.form_submit_button("➕ Tạo booking", use_container_width=True)

    if submit:
        if not guest_name.strip():
            st.error("Vui lòng nhập tên khách.")
        elif checkout <= checkin:
            st.error("Ngày check-out phải sau ngày check-in.")
        else:
            nights = (checkout - checkin).days
            room_row = rooms[rooms["Phòng"] == room_no].iloc[0]
            price = float(room_row["Giá/đêm"])
            room_total = price * nights
            discount_amount = room_total * discount / 100
            total = room_total - discount_amount
            booking_id = new_id("BK")

            existing_guest = guests[guests["SĐT"].astype(str) == str(phone)] if phone else pd.DataFrame()
            if not existing_guest.empty:
                guest_id = existing_guest.iloc[0]["Mã khách"]
            else:
                guest_id = new_id("KH")
                guest_row = {
                    "Mã khách": guest_id, "Họ tên": guest_name,
                    "CCCD/Hộ chiếu": "", "Quốc tịch": nationality,
                    "SĐT": phone, "Email": "", "Địa chỉ": "",
                    "Ghi chú": note, "Ngày tạo": now_str()
                }
                st.session_state.guests = pd.concat(
                    [st.session_state.guests, pd.DataFrame([guest_row])],
                    ignore_index=True
                )
                save_df("guests")

            booking_row = {
                "Mã booking": booking_id, "Mã khách": guest_id,
                "Khách hàng": guest_name, "Phòng": room_no,
                "Ngày đặt": now_str(), "Check-in": str(checkin),
                "Check-out": str(checkout), "Số đêm": nights,
                "Giá/đêm": price, "Tiền phòng": room_total,
                "Tiền dịch vụ": 0, "Giảm giá": discount_amount,
                "Tiền cọc": deposit, "Tổng tiền": total,
                "Còn phải trả": max(total - deposit, 0),
                "Phương thức": "Chưa thanh toán", "Trạng thái": "Đã đặt",
                "Nhân viên": user, "Ghi chú": note
            }
            st.session_state.bookings = pd.concat(
                [st.session_state.bookings, pd.DataFrame([booking_row])],
                ignore_index=True
            )
            save_df("bookings")

            log_action("Tạo booking", f"{booking_id} - P.{room_no} - {guest_name}")
            st.success(f"Đã tạo booking **{booking_id}**.")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Danh sách booking")
    st.dataframe(st.session_state.bookings, use_container_width=True, hide_index=True)


# =========================================================
# CHECK-IN / CHECK-OUT
# =========================================================
elif page == "🛎️ Check-in / Check-out":
    st.title("🛎️ Check-in / Check-out")

    bookings = st.session_state.bookings
    rooms = st.session_state.rooms

    if bookings.empty:
        st.info("Chưa có booking.")
    else:
        booking_id = st.selectbox("Chọn booking", bookings["Mã booking"].tolist())
        idx = bookings.index[bookings["Mã booking"] == booking_id][0]
        booking = bookings.loc[idx]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Khách", booking["Khách hàng"])
        c2.metric("Phòng", f"P.{booking['Phòng']}")
        c3.metric("Tổng tiền", money(booking["Tổng tiền"]))
        c4.metric("Còn trả", money(booking["Còn phải trả"]))

        st.write(
            f"**Check-in:** {booking['Check-in']}  •  "
            f"**Check-out:** {booking['Check-out']}  •  "
            f"**Trạng thái:** {booking['Trạng thái']}"
        )

        a, b, c = st.columns(3)
        with a:
            if st.button("🛎️ Xác nhận CHECK-IN", use_container_width=True):
                if booking["Trạng thái"] in ["Đã đặt"]:
                    st.session_state.bookings.at[idx, "Trạng thái"] = "Đã check-in"
                    room_idx = rooms.index[rooms["Phòng"] == booking["Phòng"]][0]
                    st.session_state.rooms.at[room_idx, "Trạng thái"] = "Đang ở"
                    st.session_state.rooms.at[room_idx, "Cập nhật cuối"] = now_str()
                    save_df("bookings")
                    save_df("rooms")
                    log_action("Check-in", f"{booking_id} - P.{booking['Phòng']}")
                    st.success("Check-in thành công.")
                    st.rerun()
                else:
                    st.warning("Booking không ở trạng thái có thể check-in.")

        with b:
            if st.button("🏁 Xác nhận CHECK-OUT", use_container_width=True):
                if booking["Trạng thái"] == "Đã check-in":
                    st.session_state.bookings.at[idx, "Trạng thái"] = "Đã check-out"
                    room_idx = rooms.index[rooms["Phòng"] == booking["Phòng"]][0]
                    st.session_state.rooms.at[room_idx, "Trạng thái"] = "Cần dọn"
                    st.session_state.rooms.at[room_idx, "Cập nhật cuối"] = now_str()
                    save_df("bookings")
                    save_df("rooms")
                    log_action("Check-out", f"{booking_id} - P.{booking['Phòng']}")
                    st.success("Check-out thành công. Phòng đã chuyển sang Cần dọn.")
                    st.rerun()
                else:
                    st.warning("Khách chưa check-in hoặc booking đã hoàn tất.")

        with c:
            if st.button("❌ Huỷ booking", use_container_width=True):
                if booking["Trạng thái"] == "Đã đặt":
                    st.session_state.bookings.at[idx, "Trạng thái"] = "Đã huỷ"
                    save_df("bookings")
                    log_action("Huỷ booking", booking_id)
                    st.success("Đã huỷ booking.")
                    st.rerun()


# =========================================================
# KHÁCH HÀNG
# =========================================================
elif page == "👤 Khách hàng":
    st.title("👤 Quản lý thông tin khách hàng")

    with st.expander("➕ Thêm hồ sơ khách hàng"):
        with st.form("guest_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Họ tên")
            idcard = c2.text_input("CCCD/Hộ chiếu")
            nationality = c3.text_input("Quốc tịch", value="Việt Nam")
            c4, c5, c6 = st.columns(3)
            phone = c4.text_input("Số điện thoại")
            email = c5.text_input("Email")
            address = c6.text_input("Địa chỉ")
            note = st.text_area("Ghi chú")
            submit = st.form_submit_button("Lưu khách hàng", use_container_width=True)

        if submit:
            if not name:
                st.error("Vui lòng nhập họ tên.")
            else:
                row = {
                    "Mã khách": new_id("KH"), "Họ tên": name,
                    "CCCD/Hộ chiếu": idcard, "Quốc tịch": nationality,
                    "SĐT": phone, "Email": email, "Địa chỉ": address,
                    "Ghi chú": note, "Ngày tạo": now_str()
                }
                st.session_state.guests = pd.concat(
                    [st.session_state.guests, pd.DataFrame([row])], ignore_index=True
                )
                save_df("guests")
                log_action("Tạo hồ sơ khách", f"{name} - {phone}")
                st.success("Đã thêm khách hàng.")
                st.rerun()

    search = st.text_input("🔎 Tìm theo tên / số điện thoại / mã khách")
    view = st.session_state.guests.copy()
    if search:
        mask = (
            view["Họ tên"].astype(str).str.contains(search, case=False, na=False)
            | view["SĐT"].astype(str).str.contains(search, case=False, na=False)
            | view["Mã khách"].astype(str).str.contains(search, case=False, na=False)
        )
        view = view[mask]

    st.dataframe(view, use_container_width=True, hide_index=True)


# =========================================================
# THANH TOÁN & FOLIO
# =========================================================
elif page == "💰 Thanh toán & Folio":
    st.title("💰 Thanh toán & Folio khách hàng")

    bookings = st.session_state.bookings
    if bookings.empty:
        st.info("Chưa có booking.")
    else:
        active = bookings[bookings["Trạng thái"] != "Đã huỷ"]
        booking_id = st.selectbox("Booking", active["Mã booking"].tolist())
        idx = bookings.index[bookings["Mã booking"] == booking_id][0]
        booking = bookings.loc[idx]

        services_total = pd.to_numeric(
            st.session_state.services_used[
                st.session_state.services_used["Mã booking"] == booking_id
            ]["Thành tiền"], errors="coerce"
        ).sum()

        total = float(booking["Tiền phòng"]) + services_total - float(booking["Giảm giá"])
        paid = pd.to_numeric(
            st.session_state.payments[
                st.session_state.payments["Mã booking"] == booking_id
            ]["Số tiền"], errors="coerce"
        ).sum()
        balance = max(total - paid, 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tiền phòng", money(booking["Tiền phòng"]))
        c2.metric("Dịch vụ", money(services_total))
        c3.metric("Đã thanh toán", money(paid))
        c4.metric("Còn phải trả", money(balance))

        st.subheader("➕ Ghi nhận thanh toán")
        with st.form("payment_form"):
            amount = st.number_input("Số tiền", min_value=0, value=int(balance), step=50000)
            method = st.selectbox("Phương thức", PAYMENT_METHODS)
            payment_type = st.selectbox("Loại", ["Thanh toán", "Tiền cọc", "Hoàn tiền"])
            submit = st.form_submit_button("💳 Xác nhận giao dịch", use_container_width=True)

        if submit:
            if amount <= 0:
                st.error("Số tiền phải lớn hơn 0.")
            else:
                row = {
                    "Mã giao dịch": new_id("GD"), "Mã booking": booking_id,
                    "Khách hàng": booking["Khách hàng"], "Thời gian": now_str(),
                    "Số tiền": amount, "Phương thức": method,
                    "Loại": payment_type, "Nhân viên": user
                }
                st.session_state.payments = pd.concat(
                    [st.session_state.payments, pd.DataFrame([row])], ignore_index=True
                )
                save_df("payments")
                log_action("Thanh toán", f"{booking_id} - {money(amount)} - {method}")
                st.success("Đã ghi nhận giao dịch.")
                st.rerun()

        st.subheader("📋 Lịch sử giao dịch")
        st.dataframe(
            st.session_state.payments[
                st.session_state.payments["Mã booking"] == booking_id
            ],
            use_container_width=True, hide_index=True
        )


# =========================================================
# HOUSEKEEPING
# =========================================================
elif page == "🧹 Housekeeping":
    st.title("🧹 Quản lý Housekeeping")
    hk = st.session_state.housekeeping
    rooms = st.session_state.rooms

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧹 Cần dọn", len(rooms[rooms["Trạng thái"] == "Cần dọn"]))
    c2.metric("⏳ Đang dọn", len(rooms[rooms["Trạng thái"] == "Đang dọn"]))
    c3.metric("🟢 Sạch", len(rooms[rooms["Trạng thái"] == "Trống - Sạch"]))
    c4.metric("🔴 Bảo trì", len(rooms[rooms["Trạng thái"] == "Bảo trì"]))

    st.subheader("📋 Tạo nhiệm vụ housekeeping")
    with st.form("hk_form"):
        c1, c2, c3 = st.columns(3)
        room_no = c1.selectbox("Phòng", rooms["Phòng"].tolist())
        task = c2.selectbox("Loại nhiệm vụ", ["Dọn phòng sau check-out", "Vệ sinh định kỳ", "Bổ sung amenities", "Kiểm tra phòng"])
        staff = c3.selectbox("Nhân viên", st.session_state.staff[st.session_state.staff["Vai trò"].isin(["housekeeping", "admin"])]["Họ tên"].tolist() or ["Chưa phân công"])
        priority = st.selectbox("Mức ưu tiên", PRIORITIES)
        submit = st.form_submit_button("➕ Tạo nhiệm vụ", use_container_width=True)

    if submit:
        row = {
            "Mã nhiệm vụ": new_id("HK"), "Phòng": room_no,
            "Loại nhiệm vụ": task, "Nhân viên": staff,
            "Mức ưu tiên": priority, "Trạng thái": "Mới",
            "Thời gian tạo": now_str(), "Thời gian hoàn thành": ""
        }
        st.session_state.housekeeping = pd.concat(
            [st.session_state.housekeeping, pd.DataFrame([row])], ignore_index=True
        )
        save_df("housekeeping")
        log_action("Tạo nhiệm vụ HK", f"P.{room_no} - {task}")
        st.success("Đã tạo nhiệm vụ.")
        st.rerun()

    st.subheader("📌 Danh sách nhiệm vụ")
    st.dataframe(hk, use_container_width=True, hide_index=True)

    if not hk.empty:
        task_id = st.selectbox("Cập nhật nhiệm vụ", hk["Mã nhiệm vụ"].tolist())
        task_idx = hk.index[hk["Mã nhiệm vụ"] == task_id][0]
        new_hk_status = st.selectbox("Trạng thái", ["Mới", "Đang xử lý", "Hoàn thành"])
        if st.button("💾 Cập nhật nhiệm vụ"):
            st.session_state.housekeeping.at[task_idx, "Trạng thái"] = new_hk_status
            if new_hk_status == "Hoàn thành":
                st.session_state.housekeeping.at[task_idx, "Thời gian hoàn thành"] = now_str()
                room_no = st.session_state.housekeeping.at[task_idx, "Phòng"]
                room_idx = rooms.index[rooms["Phòng"] == room_no][0]
                if rooms.at[room_idx, "Trạng thái"] == "Cần dọn":
                    rooms.at[room_idx, "Trạng thái"] = "Trống - Sạch"
                    rooms.at[room_idx, "Cập nhật cuối"] = now_str()
                    save_df("rooms")
            save_df("housekeeping")
            log_action("Cập nhật housekeeping", f"{task_id} → {new_hk_status}")
            st.rerun()


# =========================================================
# BẢO TRÌ
# =========================================================
elif page == "🔧 Bảo trì":
    st.title("🔧 Quản lý bảo trì")
    maint = st.session_state.maintenance
    rooms = st.session_state.rooms

    with st.form("maintenance_form"):
        c1, c2 = st.columns(2)
        room_no = c1.selectbox("Phòng", rooms["Phòng"].tolist())
        problem = c2.text_input("Thiết bị / lỗi")
        description = st.text_area("Mô tả chi tiết")
        c3, c4, c5 = st.columns(3)
        priority = c3.selectbox("Mức độ", PRIORITIES)
        staff = c4.selectbox("Nhân viên xử lý", st.session_state.staff[st.session_state.staff["Vai trò"].isin(["maintenance", "admin"])]["Họ tên"].tolist() or ["Chưa phân công"])
        cost = c5.number_input("Chi phí dự kiến", min_value=0, step=50000)
        submit = st.form_submit_button("🔧 Tạo phiếu bảo trì", use_container_width=True)

    if submit:
        row = {
            "Mã phiếu": new_id("MT"), "Phòng": room_no,
            "Thiết bị/Lỗi": problem, "Mô tả": description,
            "Mức độ": priority, "Nhân viên": staff, "Chi phí": cost,
            "Trạng thái": "Mới", "Ngày tạo": now_str(), "Ngày hoàn thành": ""
        }
        st.session_state.maintenance = pd.concat(
            [st.session_state.maintenance, pd.DataFrame([row])], ignore_index=True
        )
        room_idx = rooms.index[rooms["Phòng"] == room_no][0]
        rooms.at[room_idx, "Trạng thái"] = "Bảo trì"
        rooms.at[room_idx, "Cập nhật cuối"] = now_str()
        save_df("maintenance")
        save_df("rooms")
        log_action("Tạo phiếu bảo trì", f"P.{room_no} - {problem}")
        st.success("Đã tạo phiếu và chuyển phòng sang Bảo trì.")
        st.rerun()

    st.subheader("📋 Danh sách phiếu")
    st.dataframe(maint, use_container_width=True, hide_index=True)

    if not maint.empty:
        ticket = st.selectbox("Chọn phiếu", maint["Mã phiếu"].tolist())
        idx = maint.index[maint["Mã phiếu"] == ticket][0]
        status = st.selectbox("Trạng thái mới", MAINT_STATUS)
        if st.button("💾 Cập nhật phiếu"):
            st.session_state.maintenance.at[idx, "Trạng thái"] = status
            if status in ["Hoàn thành", "Đóng"]:
                st.session_state.maintenance.at[idx, "Ngày hoàn thành"] = now_str()
                room_no = st.session_state.maintenance.at[idx, "Phòng"]
                room_idx = rooms.index[rooms["Phòng"] == room_no][0]
                rooms.at[room_idx, "Trạng thái"] = "Trống - Sạch"
                rooms.at[room_idx, "Cập nhật cuối"] = now_str()
                save_df("rooms")
            save_df("maintenance")
            log_action("Cập nhật bảo trì", f"{ticket} → {status}")
            st.rerun()


# =========================================================
# DỊCH VỤ
# =========================================================
elif page == "🍽️ Dịch vụ":
    st.title("🍽️ Quản lý dịch vụ khách sạn")
    st.caption("Room Service • Café • Giặt ủi • Đưa đón • Spa • Bữa sáng")

    service_df = pd.DataFrame(SERVICES, columns=["Mã DV", "Dịch vụ", "Đơn giá"])
    st.dataframe(service_df, use_container_width=True, hide_index=True)

    bookings = st.session_state.bookings
    if bookings.empty:
        st.info("Cần có booking trước khi ghi nhận dịch vụ.")
    else:
        active = bookings[bookings["Trạng thái"].isin(["Đã đặt", "Đã check-in"])]
        if active.empty:
            st.info("Không có booking đang hoạt động.")
        else:
            with st.form("service_form"):
                booking_id = st.selectbox("Booking", active["Mã booking"].tolist())
                service_id = st.selectbox("Dịch vụ", service_df["Mã DV"].tolist())
                quantity = st.number_input("Số lượng", min_value=1, step=1)
                submit = st.form_submit_button("➕ Ghi nhận dịch vụ", use_container_width=True)

            if submit:
                s = service_df[service_df["Mã DV"] == service_id].iloc[0]
                b = bookings[bookings["Mã booking"] == booking_id].iloc[0]
                row = {
                    "Mã sử dụng": new_id("DV"), "Mã booking": booking_id,
                    "Khách hàng": b["Khách hàng"], "Dịch vụ": s["Dịch vụ"],
                    "Số lượng": quantity, "Đơn giá": s["Đơn giá"],
                    "Thành tiền": quantity * float(s["Đơn giá"]), "Thời gian": now_str()
                }
                st.session_state.services_used = pd.concat(
                    [st.session_state.services_used, pd.DataFrame([row])], ignore_index=True
                )
                save_df("services")
                log_action("Ghi nhận dịch vụ", f"{booking_id} - {s['Dịch vụ']}")
                st.success("Đã ghi nhận dịch vụ.")
                st.rerun()

    st.subheader("📋 Lịch sử sử dụng dịch vụ")
    st.dataframe(st.session_state.services_used, use_container_width=True, hide_index=True)


# =========================================================
# BÁO CÁO & THỐNG KÊ
# =========================================================
elif page == "📊 Báo cáo & Thống kê":
    st.title("📊 Báo cáo & Thống kê")
    bookings = st.session_state.bookings
    payments = st.session_state.payments

    if bookings.empty:
        st.info("Chưa có dữ liệu booking.")
    else:
        b = bookings.copy()
        b["Tổng tiền"] = pd.to_numeric(b["Tổng tiền"], errors="coerce").fillna(0)
        b["Tiền phòng"] = pd.to_numeric(b["Tiền phòng"], errors="coerce").fillna(0)
        b["Check-in"] = pd.to_datetime(b["Check-in"], errors="coerce")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 Tổng booking", len(b))
        c2.metric("💰 Tổng giá trị booking", money(b["Tổng tiền"].sum()))
        c3.metric("🛏️ Doanh thu phòng", money(b["Tiền phòng"].sum()))
        c4.metric("❌ Booking huỷ", len(b[b["Trạng thái"] == "Đã huỷ"]))

        st.subheader("📈 Doanh thu theo ngày đặt")
        daily = b.groupby(b["Check-in"].dt.date)["Tổng tiền"].sum().reset_index()
        daily.columns = ["Ngày", "Doanh thu"]
        if not daily.empty:
            st.line_chart(daily.set_index("Ngày"))

        st.subheader("🏨 Doanh thu theo hạng phòng")
        by_room = b.groupby("Phòng")["Tổng tiền"].sum().sort_values(ascending=False)
        st.bar_chart(by_room)

        st.subheader("📊 Công suất phòng")
        total_rooms = len(st.session_state.rooms)
        occupied = len(st.session_state.rooms[st.session_state.rooms["Trạng thái"] == "Đang ở"])
        occupancy = occupied / total_rooms * 100 if total_rooms else 0
        st.metric("Công suất hiện tại", f"{occupancy:.1f}%")

        # ADR và RevPAR theo dữ liệu booking
        completed = b[b["Trạng thái"] != "Đã huỷ"]
        room_nights = pd.to_numeric(completed["Số đêm"], errors="coerce").fillna(0).sum()
        room_revenue = completed["Tiền phòng"].sum()
        adr = room_revenue / room_nights if room_nights else 0
        revpar = room_revenue / total_rooms if total_rooms else 0

        c5, c6 = st.columns(2)
        c5.metric("ADR", money(adr))
        c6.metric("RevPAR (ước tính)", money(revpar))

        st.subheader("📥 Xuất báo cáo")
        csv = b.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Tải báo cáo booking CSV",
            data=csv,
            file_name="bao_cao_booking.csv",
            mime="text/csv",
        )


# =========================================================
# NHÂN VIÊN & PHÂN QUYỀN
# =========================================================
elif page == "👨‍💼 Nhân viên & Phân quyền":
    st.title("👨‍💼 Nhân viên & Phân quyền")

    if not can(role, ["admin"]):
        st.warning("Chỉ Quản trị viên mới được quản lý tài khoản và phân quyền.")
    else:
        st.subheader("📋 Danh sách nhân viên")
        st.dataframe(st.session_state.staff, use_container_width=True, hide_index=True)

        with st.expander("➕ Thêm nhân viên"):
            with st.form("staff_form"):
                c1, c2, c3 = st.columns(3)
                staff_name = c1.text_input("Họ tên")
                department = c2.text_input("Bộ phận")
                staff_role = c3.selectbox(
                    "Vai trò",
                    ["admin", "manager", "reception", "housekeeping", "maintenance", "accountant"]
                )
                submit = st.form_submit_button("Thêm nhân viên", use_container_width=True)

            if submit:
                row = {
                    "Mã NV": new_id("NV"), "Họ tên": staff_name,
                    "Bộ phận": department, "Vai trò": staff_role
                }
                st.session_state.staff = pd.concat(
                    [st.session_state.staff, pd.DataFrame([row])], ignore_index=True
                )
                save_df("staff")
                log_action("Thêm nhân viên", staff_name)
                st.success("Đã thêm nhân viên.")
                st.rerun()

        st.subheader("🔐 Ma trận quyền")
        permission = pd.DataFrame({
            "Chức vụ": ["Admin", "Quản lý", "Lễ tân", "Housekeeping", "Bảo trì", "Kế toán"],
            "Dashboard": ["✓", "✓", "✓", "✓", "✓", "✓"],
            "Booking": ["✓", "✓", "✓", "", "", "Xem"],
            "Check-in/out": ["✓", "✓", "✓", "", "", ""],
            "Khách hàng": ["✓", "✓", "✓", "", "", "Xem"],
            "Thanh toán": ["✓", "✓", "✓", "", "", "✓"],
            "Housekeeping": ["✓", "✓", "", "✓", "", ""],
            "Bảo trì": ["✓", "✓", "", "", "✓", ""],
            "Báo cáo": ["✓", "✓", "Hạn chế", "", "", "✓"],
        })
        st.dataframe(permission, use_container_width=True, hide_index=True)


# =========================================================
# NHẬT KÝ
# =========================================================
elif page == "📋 Nhật ký hoạt động":
    st.title("📋 Nhật ký hoạt động hệ thống")
    logs = st.session_state.logs

    if logs.empty:
        st.info("Chưa có hoạt động.")
    else:
        user_filter = st.selectbox("Nhân viên", ["Tất cả"] + sorted(logs["Nhân viên"].unique().tolist()))
        view = logs
        if user_filter != "Tất cả":
            view = view[view["Nhân viên"] == user_filter]
        st.dataframe(view.sort_values("Thời gian", ascending=False), use_container_width=True, hide_index=True)

        csv = view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Xuất nhật ký CSV",
            data=csv,
            file_name="nhat_ky_he_thong.csv",
            mime="text/csv",
        )


# -------------------- FOOTER --------------------
st.sidebar.markdown("---")
st.sidebar.caption("🏨 GRAND RIVER HOTEL • 4★")
st.sidebar.caption("Hệ thống quản lý nội bộ • Demo")
