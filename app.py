import sqlite3
from datetime import date, datetime, timedelta
import openai
import pandas as pd
import streamlit as st

# =========================================================
# 1. CẤU HÌNH TRANG & BIẾN HẰNG SỐ
# =========================================================
st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn & AI Assistant",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        room_type TEXT NOT NULL,
        price_per_night REAL NOT NULL,
        status TEXT DEFAULT 'Trống'
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        display_name TEXT,
        message TEXT,
        created_at TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        created_at TIMESTAMP
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
        INSERT INTO employees (full_name, username, password, role, phone, active, created_at)
        VALUES ('Quản trị viên', 'admin', 'admin123', 'Quản trị viên', '0901234567', 1, ?)
        """,
            (datetime.now(),),
        )

        cursor.executemany(
            """
        INSERT INTO rooms (room_number, room_type, price_per_night, status)
        VALUES (?, ?, ?, ?)
        """,
            [
                ("101", "Đơn", 500000, "Trống"),
                ("102", "Đôi", 800000, "Đang ở"),
                ("201", "VIP", 1500000, "Bảo trì"),
                ("202", "Gia đình", 1200000, "Đã đặt"),
            ],
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
    return f"{val:,.0f} VNĐ"


def get_rooms():
    return read_df(
        "SELECT id, room_number AS `Số phòng`, room_type AS `Loại phòng`, price_per_night AS `Giá/Đêm`, status AS `Trạng thái` FROM rooms"
    )


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
        "<h2 style='text-align: center;'>🏨 HỆ THỐNG QUẢN LÝ KHÁCH SẠN</h2>",
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
        "🌐 Trợ lý AI OpenRouter",
        "👨‍💼 Phân quyền nhân viên",
    ]

    page = st.sidebar.radio(
        "Điều hướng menu", page_options, key="main_navigation_radio"
    )

    if st.sidebar.button(
        "🚪 Đăng xuất", use_container_width=True, key="btn_logout_sidebar"
    ):
        log_action(user["username"], "Đăng xuất")
        st.session_state["user"] = None
        st.rerun()

    st.sidebar.divider()

    # --- 1. SƠ ĐỒ PHÒNG ---
    if page == "🏨 Sơ đồ phòng":
        st.title("🏨 Sơ đồ & Quản lý danh sách phòng")

        rooms_df = get_rooms()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng số phòng", len(rooms_df))
        c2.metric(
            "Phòng trống", len(rooms_df[rooms_df["Trạng thái"] == "Trống"])
        )
        c3.metric(
            "Đang ở / Đã đặt",
            len(rooms_df[rooms_df["Trạng thái"].isin(["Đang ở", "Đã đặt"])]),
        )
        c4.metric(
            "Bảo trì", len(rooms_df[rooms_df["Trạng thái"] == "Bảo trì"])
        )

        st.divider()

        status_colors = {
            "Trống": "#28a745",
            "Đang ở": "#dc3545",
            "Đã đặt": "#ffc107",
            "Bảo trì": "#6c757d",
        }

        cols = st.columns(4)
        for idx, row in rooms_df.iterrows():
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
                        border-left: 5px solid {bg_color};
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

        with st.expander("📄 Xem bảng chi tiết"):
            st.dataframe(rooms_df, use_container_width=True, hide_index=True)

        if role_allowed("Quản trị viên") or role_allowed("Lễ tân"):
            with st.expander("➕ Cập nhật trạng thái phòng nhanh"):
                with st.form("update_room_status"):
                    selected_room = st.selectbox(
                        "Chọn phòng",
                        rooms_df["Số phòng"].tolist(),
                        key="select_room_update",
                    )
                    new_status = st.selectbox(
                        "Trạng thái mới",
                        ROOM_STATUSES,
                        key="select_status_update",
                    )
                    btn_update = st.form_submit_button("Cập nhật")
                    if btn_update:
                        execute_sql(
                            "UPDATE rooms SET status=:status WHERE room_number=:room_num",
                            {"status": new_status, "room_num": selected_room},
                        )
                        st.success(
                            f"Đã cập nhật phòng {selected_room} sang '{new_status}'"
                        )
                        st.rerun()

    # --- 2. QUẢN LÝ SỰ CỐ & BẢO TRÌ ---
    elif page == "🔧 Quản lý sự cố & bảo trì":
        st.title("🔧 Quản lý sự cố & bảo trì")
        tab_report, tab_list = st.tabs(
            ["🚨 Báo cáo sự cố mới", "📋 Danh sách sự cố"]
        )

        rooms_df = read_df("SELECT id, room_number FROM rooms")
        room_map = {"Khu vực chung / Khác": None}
        for _, r in rooms_df.iterrows():
            room_map[f"Phòng {r['room_number']}"] = r["id"]

        with tab_report:
            with st.form("maint_form"):
                selected_loc = st.selectbox(
                    "Vị trí",
                    list(room_map.keys()),
                    key="maint_location_select",
                )
                title = st.text_input(
                    "Tiêu đề sự cố / yêu cầu *", key="maint_title_input"
                )
                description = st.text_area(
                    "Mô tả chi tiết", key="maint_desc_input"
                )
                priority = st.selectbox(
                    "Mức độ ưu tiên",
                    PRIORITIES,
                    index=1,
                    key="maint_priority_select",
                )
                assigned_to = st.text_input(
                    "Nhân viên xử lý",
                    "Chưa phân công",
                    key="maint_assign_input",
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
                        execute_sql(
                            "UPDATE rooms SET status='Bảo trì' WHERE id=:id",
                            {"id": room_id},
                        )

                    log_action(
                        user["username"], f"Báo cáo sự cố bảo trì: {title}"
                    )
                    st.success("✅ Đã gửi báo cáo bảo trì thành công!")
                    st.rerun()

        with tab_list:
            maint_df = read_df(
                """
                SELECT 
                    m.id AS `ID`,
                    COALESCE('P.' || r.room_number, 'Khu vực chung') AS `Vị trí`,
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
                c_sel, c_stat, c_btn = st.columns([1, 1, 1])
                with c_sel:
                    m_id = st.selectbox(
                        "Chọn mã sự cố",
                        maint_df["ID"].tolist(),
                        key="maint_id_select",
                    )
                with c_stat:
                    m_status = st.selectbox(
                        "Trạng thái mới",
                        MAINTENANCE_STATUSES,
                        key="maint_status_select",
                    )

                with c_btn:
                    st.write("")
                    st.write("")
                    if st.button(
                        "💾 Cập nhật",
                        use_container_width=True,
                        key="btn_update_maint",
                    ):
                        completed_at = (
                            datetime.now() if m_status == "Hoàn thành" else None
                        )
                        execute_sql(
                            """
                            UPDATE maintenance 
                            SET status=:status, completed_at=:completed_at 
                            WHERE id=:id
                            """,
                            {
                                "status": m_status,
                                "completed_at": completed_at,
                                "id": int(m_id),
                            },
                        )

                        target_room = read_df(
                            "SELECT room_id FROM maintenance WHERE id=:id",
                            {"id": int(m_id)},
                        )
                        if (
                            not target_room.empty
                            and target_room.iloc[0]["room_id"]
                            and m_status == "Hoàn thành"
                        ):
                            execute_sql(
                                "UPDATE rooms SET status='Trống' WHERE id=:id",
                                {
                                    "id": int(
                                        target_room.iloc[0]["room_id"]
                                    )
                                },
                            )

                        log_action(
                            user["username"],
                            f"Cập nhật sự cố #{m_id} -> {m_status}",
                        )
                        st.success("✅ Đã cập nhật trạng thái sự cố.")
                        st.rerun()

    # --- 3. BÁO CÁO DOANH THU ---
    elif page == "📊 Báo cáo doanh thu":
        st.title("📊 Báo cáo doanh thu")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input(
                "Từ ngày",
                date.today() - timedelta(days=30),
                key="rev_start_date",
            )
        with c2:
            end_date = st.date_input("Đến ngày", date.today(), key="rev_end_date")

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
            st.info(
                "Chưa có dữ liệu thanh toán phát sinh trong khoảng thời gian này."
            )
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

    # --- 5. CHATBOX / BÌNH LUẬN NỘI BỘ ---
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

        if prompt := st.chat_input(
            "Nhập tin nhắn nội bộ...", key="internal_chat_input"
        ):
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

    # --- 6. TRỢ LÝ AI OPENROUTER ---
    elif page == "🌐 Trợ lý AI OpenRouter":
        st.title("🌐 Trợ lý AI OpenRouter")

        default_api_key = st.secrets.get("OPENROUTER_API_KEY", "")

        with st.sidebar:
            st.markdown("---")
            st.subheader("⚙️ Cấu hình OpenRouter")
            openrouter_key = st.text_input(
                "OpenRouter API Key (sk-or-v1-...):",
                value=default_api_key,
                type="password",
                key="openrouter_api_key_sidebar_input",
            )
     ai_model = st.selectbox(
         "Chọn mô hình AI:",
    [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-r1:free",
    ],
         key="openrouter_model_select_box",
)

            if st.button(
                "🗑️ Xóa lịch sử Chat AI",
                use_container_width=True,
                key="btn_clear_ai_history",
            ):
                st.session_state["ai_messages"] = []
                st.rerun()

        # Hiển thị lịch sử Chatbot
        for msg in st.session_state["ai_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input(
            "Hỏi Trợ lý AI...", key="openrouter_chat_input"
        ):
            if not openrouter_key:
                st.error(
                    "⚠️ Vui lòng nhập OpenRouter API Key (bắt đầu bằng sk-or-v1-...) ở Sidebar góc trái!"
                )
            else:
                st.session_state["ai_messages"].append(
                    {"role": "user", "content": user_prompt}
                )
                with st.chat_message("user"):
                    st.markdown(user_prompt)

                with st.chat_message("assistant"):
                    status_placeholder = st.empty()
                    status_placeholder.markdown("🔄 *AI đang kết nối OpenRouter...*")

                    try:
                        # Kết nối OpenRouter qua OpenAI SDK bằng base_url
                        client = openai.OpenAI(
                            base_url="https://openrouter.ai/api/v1",
                            api_key=openrouter_key,
                        )

                        messages = [
                            {
                                "role": "system",
                                "content": "Bạn là trợ lý AI thông minh hỗ trợ vận hành và quản lý khách sạn.",
                            }
                        ]
                        for m in st.session_state["ai_messages"]:
                            messages.append(
                                {"role": m["role"], "content": m["content"]}
                            )

                        response = client.chat.completions.create(
                            model=ai_model,
                            messages=messages,
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

    # --- 7. PHÂN QUYỀN NHÂN VIÊN (CHỈ ADMIN) ---
    elif page == "👨‍💼 Phân quyền nhân viên":
        if not role_allowed("Quản trị viên"):
            st.error("⛔ Bạn không có quyền truy cập chức năng này.")
        else:
            st.title("👨‍💼 Quản lý nhân viên & Phân quyền")

            tab_list_emp, tab_add_emp = st.tabs(
                ["📋 Danh sách nhân viên", "➕ Thêm nhân viên"]
            )

            with tab_list_emp:
                emp_df = read_df(
                    """
                    SELECT 
                        id AS `ID`,
                        full_name AS `Họ và tên`,
                        username AS `Tài khoản`,
                        role AS `Chức vụ`,
                        phone AS `Số điện thoại`,
                        CASE WHEN active = 1 THEN 'Hoạt động' ELSE 'Khóa' END AS `Trạng thái`,
                        created_at AS `Ngày tạo`
                    FROM employees
                    ORDER BY id DESC
                    """
                )
                st.dataframe(emp_df, use_container_width=True, hide_index=True)

            with tab_add_emp:
                with st.form("add_employee_form"):
                    emp_name = st.text_input(
                        "Họ tên nhân viên *", key="emp_fullname_input"
                    )
                    emp_user = st.text_input(
                        "Tên tài khoản *", key="emp_username_input"
                    )
                    emp_pass = st.text_input(
                        "Mật khẩu *", type="password", key="emp_password_input"
                    )
                    emp_role = st.selectbox(
                        "Chức vụ / Vai trò", ROLES, key="emp_role_select"
                    )
                    emp_phone = st.text_input(
                        "Số điện thoại", key="emp_phone_input"
                    )
                    emp_submit = st.form_submit_button(
                        "💾 Lưu nhân viên", use_container_width=True
                    )

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
                            log_action(
                                user["username"],
                                f"Thêm nhân viên mới: {emp_user.strip()}",
                            )
                            st.success("✅ Thêm nhân viên thành công!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Tên tài khoản đã tồn tại trên hệ thống!")
                        except Exception as e:
                            st.error(f"❌ Có lỗi xảy ra: {e}")


if __name__ == "__main__":
    main()
