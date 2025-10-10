import psycopg
from contextlib import contextmanager
import os
import streamlit as st

def get_database_config():
    """取得資料庫連線設定 - 上線版本（使用環境變數或 Streamlit Secrets）"""
    try:
        # 優先使用 Streamlit Secrets（部署到 Streamlit Cloud 時）
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            return {
                'host': st.secrets['database']['host'],
                'dbname': st.secrets['database']['dbname'],
                'user': st.secrets['database']['user'],
                'password': st.secrets['database']['password'],
                'port': st.secrets['database']['port'],
                'sslmode': st.secrets['database'].get('sslmode', 'require')
            }
        # 其次使用環境變數（本地開發或其他部署環境）
        else:
            return {
                'host': os.getenv('DB_HOST', 'localhost'),
                'dbname': os.getenv('DB_NAME', 'neondb'),
                'user': os.getenv('DB_USER', 'neondb_owner'),
                'password': os.getenv('DB_PASSWORD'),
                'port': os.getenv('DB_PORT', '5432'),
                'sslmode': os.getenv('DB_SSLMODE', 'require')
            }
    except Exception as e:
        raise RuntimeError(f"❌ 無法讀取資料庫設定：{e}")

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
