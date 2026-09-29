import pandas as pd
import sqlite3
import streamlit as st
from datetime import datetime, date, timedelta

# =========================================================
# 1. CẤU HÌNH TRANG & DỮ LIỆU MẪU
# =========================================================
st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "hotel_management.db"

ROOM_TYPES = ["Đơn", "Đôi", "VIP", "Gia đình"]
ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bảo trì"]
MAINTENANCE_STATUSES = ["Mới", "Đang xử lý", "Hoàn thành", "Hủy"]
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
ROLES = ["Lễ tân", "Bảo trì", "Kế toán", "Quản lý", "Quản trị viên"]

# =========================================================
# 2. KHỞI TẠO CƠ SỞ DỮ LIỆU (SQLITE)
# =========================================================
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Bảng nhân viên
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

    # Bảng phòng
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        room_type TEXT NOT NULL,
        price_per_night REAL NOT NULL,
        status TEXT DEFAULT 'Trống'
    )
    """)

    # Bảng bảo trì
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

    # Bảng thanh toán / doanh thu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        customer_name TEXT,
        amount REAL NOT NULL,
        paid_at TIMESTAMP,
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    )
    """)

    # Bảng nhắn tin
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        display_name TEXT,
        message TEXT,
        created_at TIMESTAMP
    )
    """)

    # Bảng nhật ký hoạt động
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        created_at TIMESTAMP
    )
    """)

    # Thêm tài khoản Admin mặc định nếu chưa có
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO employees (full_name, username, password, role, phone, active, created_at)
        VALUES ('Quản trị viên', 'admin', 'admin123', 'Quản trị viên', '0901234567', 1, ?)
        """, (datetime.now(),))
        
        # Thêm một vài phòng mẫu
        cursor.executemany("""
        INSERT INTO rooms (room_number, room_type, price_per_night, status)
        VALUES (?, ?, ?, ?)
        """, [
            ("101", "Đơn", 500000, "Trống"),
            ("102", "Đôi", 800000, "Trống"),
            ("201", "VIP", 1500000, "Bảo trì"),
            ("202", "Gia đình", 1200000, "Trống")
        ])

    conn.commit()
    conn.close()

# Khoản hỗ trợ thao tác DB
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
        (username, action, datetime.now())
    )

def money(val):
    return f"{val:,.0f} VNĐ"

def get_rooms():
    return read_df("SELECT id, room_number AS `Số phòng`, room_type AS `Loại phòng`, price_per_night AS `Giá/Đêm`, status AS `Trạng thái` FROM rooms")

# Initialize DB at startup
init_db()

# =========================================================
# 3. QUẢN LÝ ĐĂNG NHẬP & PHÂN QUYỀN
# =========================================================
if "user" not in st.session_state:
    st.session_state["user"] = None

def login_screen():
    st.markdown("<h2 style='text-align: center;'>🏨 DỰ ÁN QUẢN LÝ KHÁCH SẠN</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔑 Đăng nhập hệ thống")
            username = st.text_input("Tên tài khoản")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submit:
                res = read_df(
                    "SELECT * FROM employees WHERE username=:u AND password=:p AND active=1",
                    {"u": username, "p": password}
                )
                if not res.empty:
                    user_info = res.iloc[0].to_dict()
                    st.session_state["user"] = user_info
                    log_action(user_info["username"], "Đăng nhập thành công")
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("❌ Tên tài khoản hoặc mật khẩu không chính xác!")

def role_allowed(required_role):
    user = st.session_state.get("user")
    if not user:
        return False
    if user["role"] == "Quản trị viên":
        return True
    return user["role"] == required_role

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
        "🏨 Sơ đồ phòng",
        "🔧 Quản lý sự cố & bảo trì",
        "📊 Báo cáo doanh thu",
        "📈 Công suất phòng",
        "💬 Chatbox / Bình luận",
        "👨‍💼 Phân quyền nhân viên"
    ]
    
    page = st.sidebar.radio("Điều hướng menu", page_options)

    if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
        log_action(user["username"], "Đăng xuất")
        st.session_state["user"] = None
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption("Hệ thống Quản lý Khách sạn v2.0")

    # --- 1. SƠ ĐỒ PHÒNG ---
    if page == "🏨 Sơ đồ phòng":
        st.title("🏨 Sơ đồ & Quản lý danh sách phòng")
        
        rooms_df = get_rooms()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng số phòng", len(rooms_df))
        col2.metric("Phòng trống", len(rooms_df[rooms_df["Trạng thái"] == "Trống"]))
        col3.metric("Đang ở / Đã đặt", len(rooms_df[rooms_df["Trạng thái"].isin(["Đang ở", "Đã đặt"])]))
        col4.metric("Bảo trì", len(rooms_df[rooms_df["Trạng thái"] == "Bảo trì"]))
        
        st.divider()
        st.dataframe(rooms_df, use_container_width=True, hide_index=True)

        if role_allowed("Quản trị viên") or role_allowed("Lễ tân"):
            with st.expander("➕ Cập nhật trạng thái phòng nhanh"):
                with st.form("update_room_status"):
                    selected_room = st.selectbox("Chọn phòng", rooms_df["Số phòng"].tolist())
                    new_status = st.selectbox("Trạng thái mới", ROOM_STATUSES)
                    btn_update = st.form_submit_button("Cập nhật")
                    if btn_update:
                        execute_sql(
                            "UPDATE rooms SET status=:status WHERE room_number=:room_num",
                            {"status": new_status, "room_num": selected_room}
                        )
                        st.success(f"Đã cập nhật phòng {selected_room} sang '{new_status}'")
                        st.rerun()

    # --- 2. QUẢN LÝ SỰ CỐ & BẢO TRÌ ---
    elif page == "🔧 Quản lý sự cố & bảo trì":
        st.title("🔧 Quản lý sự cố & Bảo trì phòng")

        tab_report, tab_list = st.tabs(["🚨 Báo cáo sự cố mới", "📋 Danh sách sự cố"])

        rooms_df = read_df("SELECT id, room_number FROM rooms")
        room_map = {"Khu vực chung / Khác": None}
        for _, r in rooms_df.iterrows():
            room_map[f"Phòng {r['room_number']}"] = r["id"]

        with tab_report:
            with st.form("maint_form"):
                selected_loc = st.selectbox("Vị trí", list(room_map.keys()))
                title = st.text_input("Tiêu đề sự cố / yêu cầu *")
                description = st.text_area("Mô tả chi tiết")
                priority = st.selectbox("Mức độ ưu tiên", PRIORITIES, index=1)
                assigned_to = st.text_input("Nhân viên xử lý", "Chưa phân công")
                submit_maint = st.form_submit_button("🚨 Gửi báo cáo bảo trì", use_container_width=True)

            if submit_maint:
                if not title.strip():
                    st.error("Vui lòng nhập tiêu đề sự cố.")
                else:
                    room_id = room_map[selected_loc]
                    execute_sql(
                        """
                        INSERT INTO maintenance (room_id, title, description, priority, status, assigned_to, created_at)
                        VALUES (:room_id, :title, :description, :priority, 'Mới', :assigned_to, :created_at)
                        """,
                        {
                            "room_id": room_id,
                            "title": title.strip(),
                            "description": description,
                            "priority": priority,
                            "assigned_to": assigned_to,
                            "created_at": datetime.now(),
                        },
                    )
                    if room_id:
                        execute_sql("UPDATE rooms SET status='Bảo trì' WHERE id=:id", {"id": room_id})

                    log_action(user["username"], f"Báo cáo sự cố bảo trì: {title}")
                    st.success("✅ Đã gửi báo cáo bảo trì thành công!")
                    st.rerun()

        with tab_list:
            maint_df = read_df(
                """
                SELECT 
                    m.id AS `ID`,
                    COALESCE(CONCAT('P.', r.room_number), 'Khu vực chung') AS `Vị trí`,
                    m.title AS `Sự cố`,
                    m.description AS `Mô tả`,
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

            if not maint_df.empty:
                st.divider()
                st.subheader("🔄 Cập nhật tiến độ bảo trì")
                m_id = st.selectbox("Chọn mã sự cố", maint_df["ID"].tolist())
                m_status = st.selectbox("Trạng thái mới", MAINTENANCE_STATUSES)
                
                if st.button("💾 Cập nhật bảo trì"):
                    completed_at = datetime.now() if m_status == "Hoàn thành" else None
                    execute_sql(
                        """
                        UPDATE maintenance 
                        SET status=:status, completed_at=:completed_at 
                        WHERE id=:id
                        """,
                        {"status": m_status, "completed_at": completed_at, "id": int(m_id)},
                    )
                    
                    target_room = read_df("SELECT room_id FROM maintenance WHERE id=:id", {"id": int(m_id)})
                    if not target_room.empty and target_room.iloc[0]["room_id"] and m_status == "Hoàn thành":
                        execute_sql("UPDATE rooms SET status='Trống' WHERE id=:id", {"id": int(target_room.iloc[0]["room_id"])})

                    log_action(user["username"], f"Cập nhật sự cố #{m_id} -> {m_status}")
                    st.success("✅ Đã cập nhật trạng thái sự cố.")
                    st.rerun()

    # --- 3. BÁO CÁO DOANH THU ---
    elif page == "📊 Báo cáo doanh thu":
        st.title("📊 Báo cáo doanh thu")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Từ ngày", date.today() - timedelta(days=30))
        with c2:
            end_date = st.date_input("Đến ngày", date.today())

        df_rev = read_df(
            """
            SELECT 
                DATE(paid_at) AS `Ngày`,
                SUM(amount) AS `Doanh thu`,
                COUNT(id) AS `Số giao dịch`
            FROM payments
            WHERE DATE(paid_at) BETWEEN :start AND :end
            GROUP BY DATE(paid_at)
            ORDER BY Ngày ASC
            """,
            {"start": start_date, "end": end_date},
        )

        if df_rev.empty:
            st.info("Chưa có dữ liệu thanh toán phát sinh trong khoảng thời gian này.")
        else:
            total_rev = df_rev["Doanh thu"].sum()
            st.metric("💸 Tổng doanh thu", money(total_rev))
            st.line_chart(df_rev.set_index("Ngày")["Doanh thu"])
            st.dataframe(df_rev, use_container_width=True, hide_index=True)

    # --- 4. CÔNG SUẤT PHÒNG ---
    elif page == "📈 Công suất phòng":
        st.title("📈 Thống kê công suất phòng")

        rooms = get_rooms()
        status_counts = rooms["Trạng thái"].value_counts().reset_index()
        status_counts.columns = ["Trạng thái", "Số lượng"]

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Phân bố trạng thái phòng")
            st.dataframe(status_counts, use_container_width=True, hide_index=True)
        with col2:
            st.bar_chart(status_counts.set_index("Trạng thái"))

    # --- 5. CHATBOX / BÌNH LUẬN ---
    elif page == "💬 Chatbox / Bình luận":
        st.title("💬 Kênh trao đổi nội bộ")

        messages = read_df(
            """
            SELECT display_name AS `Người gửi`, message AS `Nội dung`, created_at AS `Thời gian`
            FROM chat_messages
            ORDER BY id DESC
            LIMIT 50
            """
        )

        for _, msg in messages.iloc[::-1].iterrows():
            with st.chat_message("user"):
                st.write(f"**{msg['Người gửi']}** *({msg['Thời gian']})*")
                st.write(msg["Nội dung"])

        if prompt := st.chat_input("Nhập tin nhắn nội bộ..."):
            execute_sql(
                """
                INSERT INTO chat_messages (username, display_name, message, created_at)
                VALUES (:username, :display_name, :message, :created_at)
                """,
                {
                    "username": user["username"],
                    "display_name": user["full_name"],
                    "message": prompt,
                    "created_at": datetime.now(),
                },
            )
            st.rerun()

    # --- 6. PHÂN QUYỀN NHÂN VIÊN ---
    elif page == "👨‍💼 Phân quyền nhân viên":
        if not role_allowed("Quản trị viên"):
            st.error("⛔ Bạn không có quyền truy cập chức năng này.")
        else:
            st.title("👨‍💼 Quản lý nhân viên & Phân quyền")

            tab_list_emp, tab_add_emp = st.tabs(["📋 Danh sách nhân viên", "➕ Thêm nhân viên"])

            with tab_add_emp:
                with st.form("add_employee_form"):
                    emp_name = st.text_input("Họ tên nhân viên *")
                    emp_user = st.text_input("Tên tài khoản *")
                    emp_pass = st.text_input("Mật khẩu *", type="password")
                    emp_role = st.selectbox("Chức vụ / Vai trò", ROLES)
                    emp_phone = st.text_input("Số điện thoại")
                    emp_submit = st.form_submit_button("💾 Lưu nhân viên", use_container_width=True)

                if emp_submit:
                    if not emp_name or not emp_user or not emp_pass:
                        st.error("Vui lòng điền đầy đủ thông tin bắt buộc.")
                    else:
                        try:
                            execute_sql(
                                """
                                INSERT INTO employees (full_name, username, password, role, phone, active, created_at)
                                VALUES (:name, :username, :password, :role, :phone, 1, :created_at)
                                """,
                                {
                                    "name": emp_name.strip(),
                                    "username": emp_user.strip(),
                                    "password": emp_pass.strip(),
                                    "role": emp_role,
                                    "phone": emp_phone,
                                    "created_at": datetime.now(),
                                },
                            )
                            log_action(user["username"], f"Thêm nhân viên mới {emp_user}")
                            st.success("✅ Thêm nhân viên thành công!")
                            st.rerun()
                        except Exception as err:
                            st.error("Lỗi khi thêm nhân viên (Tên tài khoản có thể đã tồn tại).")

            with tab_list_emp:
                emp_df = read_df(
                    """
                    SELECT id AS `ID`, full_name AS `Họ tên`, username AS `Tài khoản`, role AS `Chức vụ`, phone AS `SĐT`, active AS `Kích hoạt`
                    FROM employees
                    ORDER BY id ASC
                    """
                )
                st.dataframe(emp_df, use_container_width=True, hide_index=True)

# =========================================================
# 5. ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH
# =========================================================
if __name__ == "__main__":
    main()
