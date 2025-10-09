import psycopg
import streamlit as st
from contextlib import contextmanager

def get_database_config():
    """取得資料庫連線設定 - 從 Streamlit Cloud Secrets 讀取"""
    return {
        'host': st.secrets.get('DB_HOST'),
        'database': st.secrets.get('DB_NAME'),
        'user': st.secrets.get('DB_USER'),
        'password': st.secrets.get('DB_PASSWORD'),
        'port': st.secrets.get('DB_PORT', '5432'),
        'sslmode': st.secrets.get('DB_SSLMODE', 'require')
    }

def get_connection():
    """建立資料庫連線"""
    try:
        config = get_database_config()
        return psycopg.connect(**config)
    except Exception as e:
        raise RuntimeError(f"❌ 資料庫連線失敗：{e}")

@contextmanager
def get_cursor():
    """取得資料庫游標（自動處理連線與游標關閉）"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
