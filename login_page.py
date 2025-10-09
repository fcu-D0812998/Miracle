import streamlit as st
import bcrypt
from db_config import get_connection

def login_page():
    st.title("🔐 使用者登入")

    username = st.text_input("帳號")
    password = st.text_input("密碼", type="password")

    if st.button("登入"):
        if not username or not password:
            st.warning("請輸入帳號與密碼。")
            return

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, password_hash FROM users WHERE username = %s", 
                        (username,)
                    )
                    user = cur.fetchone()

            if not user:
                st.error("❌ 帳號或密碼錯誤。")
                return

            user_id, username, password_hash = user
            
            # 處理 password_hash 可能是 str 或 bytes
            if isinstance(password_hash, str):
                password_hash = password_hash.encode("utf-8")

            if bcrypt.checkpw(password.encode("utf-8"), password_hash):
                st.session_state["user"] = {
                    "id": user_id, 
                    "username": username
                }
                st.success("✅ 登入成功！")
                st.rerun()
            else:
                st.error("❌ 帳號或密碼錯誤。")
                
        except Exception as e:
            st.error(f"❌ 資料庫連線失敗：{e}")
