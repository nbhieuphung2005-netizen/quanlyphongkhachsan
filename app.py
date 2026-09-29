import streamlit as st
from google import genai
from google.genai import types

# =========================================================
# 1. CẤU HÌNH TRANG
# =========================================================
st.set_page_config(
    page_title="Trợ lý AI Gemini",
    page_icon="🤖",
    layout="wide"
)

# =========================================================
# 2. KHỞI TẠO SESSION STATE (LƯU LỊCH SỬ CHAT)
# =========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# 3. SIDEBAR - CẤU HÌNH API KEY & MÔ HÌNH
# =========================================================
with st.sidebar:
    st.title("⚙️ Cấu hình AI")
    
    # Nhập Gemini API Key
    api_key = st.text_input("Nhập Google Gemini API Key:", type="password")
    
    # Chọn mô hình AI
    model_option = st.selectbox(
        "Chọn mô hình Gemini:",
        ["gemini-2.5-flash", "gemini-2.5-pro"]
    )
    
    # Nút xóa lịch sử chat
    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("💡 **Mẹo:** Dùng `gemini-2.5-flash` cho phản hồi nhanh và `gemini-2.5-pro` cho các câu hỏi suy luận phức tạp.")

# =========================================================
# 4. GIAO DIỆN CHATBOT MAIN
# =========================================================
st.title("🤖 Trợ lý AI Thông Minh (Gemini)")
st.caption("Chatbot hiện đại kết nối trực tiếp với Google Gemini API")

# Hiển thị các tin nhắn đã trò chuyện trước đó
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Nhập câu hỏi từ người dùng
if prompt := st.chat_input("Hỏi AI bất kỳ điều gì..."):
    
    # Kiểm tra xem thầy đã nhập API Key chưa
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key ở thanh bên trái (Sidebar) để bắt đầu!")
        st.stop()

    # 1. Hiển thị tin nhắn người dùng lên UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Gửi yêu cầu tới Gemini API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🔄 *AI đang suy nghĩ...*")
        
        try:
            # Khởi tạo Client Gemini
            client = genai.Client(api_key=api_key)
            
            # Chuyển đổi lịch sử chat sang định dạng của SDK Gemini
            contents = []
            for msg in st.session_state.messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

            # Gọi API sinh phản hồi
            response = client.models.generate_content(
                model=model_option,
                contents=contents
            )
            
            ai_response = response.text
            
            # Hiển thị kết quả ra màn hình
            message_placeholder.markdown(ai_response)
            
            # Lưu câu trả lời của AI vào lịch sử
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

        except Exception as e:
            message_placeholder.error(f"❌ Đã xảy ra lỗi khi kết nối API: {e}")
import streamlit as st
from google import genai
from google.genai import types

# =========================================================
# 1. CẤU HÌNH TRANG
# =========================================================
st.set_page_config(
    page_title="Trợ lý AI Gemini",
    page_icon="🤖",
    layout="wide"
)

# =========================================================
# 2. KHỞI TẠO SESSION STATE (LƯU LỊCH SỬ CHAT)
# =========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# 3. SIDEBAR - CẤU HÌNH API KEY & MÔ HÌNH
# =========================================================
with st.sidebar:
    st.title("⚙️ Cấu hình AI")
    
    # Nhập Gemini API Key
    api_key = st.text_input("Nhập Google Gemini API Key:", type="password")
    
    # Chọn mô hình AI
    model_option = st.selectbox(
        "Chọn mô hình Gemini:",
        ["gemini-2.5-flash", "gemini-2.5-pro"]
    )
    
    # Nút xóa lịch sử chat
    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("💡 **Mẹo:** Dùng `gemini-2.5-flash` cho phản hồi nhanh và `gemini-2.5-pro` cho các câu hỏi suy luận phức tạp.")

# =========================================================
# 4. GIAO DIỆN CHATBOT MAIN
# =========================================================
st.title("🤖 Trợ lý AI Thông Minh (Gemini)")
st.caption("Chatbot hiện đại kết nối trực tiếp với Google Gemini API")

# Hiển thị các tin nhắn đã trò chuyện trước đó
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Nhập câu hỏi từ người dùng
if prompt := st.chat_input("Hỏi AI bất kỳ điều gì..."):
    
    # Kiểm tra xem thầy đã nhập API Key chưa
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key ở thanh bên trái (Sidebar) để bắt đầu!")
        st.stop()

    # 1. Hiển thị tin nhắn người dùng lên UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Gửi yêu cầu tới Gemini API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🔄 *AI đang suy nghĩ...*")
        
        try:
            # Khởi tạo Client Gemini
            client = genai.Client(api_key=api_key)
            
            # Chuyển đổi lịch sử chat sang định dạng của SDK Gemini
            contents = []
            for msg in st.session_state.messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

            # Gọi API sinh phản hồi
            response = client.models.generate_content(
                model=model_option,
                contents=contents
            )
            
            ai_response = response.text
            
            # Hiển thị kết quả ra màn hình
            message_placeholder.markdown(ai_response)
            
            # Lưu câu trả lời của AI vào lịch sử
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

        except Exception as e:
            message_placeholder.error(f"❌ Đã xảy ra lỗi khi kết nối API: {e}")
