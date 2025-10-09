import psycopg
import os
from dotenv import load_dotenv
from contextlib import contextmanager

# 載入 .env 檔案
load_dotenv()

def get_connection():
    """建立資料庫連線"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL 環境變數未設定。請檢查 .env 檔案。")
    return psycopg.connect(db_url)

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
