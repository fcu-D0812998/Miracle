import psycopg
import bcrypt
import getpass

# === Neon 資料庫連線設定 ===
DB_URL = "postgresql://neondb_owner:npg_qtAB6EhysQK9@ep-curly-voice-a14v87l0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# === 建立連線 ===
def get_connection():
    return psycopg.connect(DB_URL)

def main():
    print("🔐 新增使用者帳號（最簡版）")
    username = input("請輸入帳號: ").strip()

    password = getpass.getpass("請輸入密碼: ")
    confirm = getpass.getpass("再次輸入密碼: ")

    if password != confirm:
        print("❌ 密碼不一致，請重新輸入。")
        return

    # 產生 bcrypt 雜湊
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                """, (username, hashed))
                conn.commit()
                print(f"✅ 成功新增使用者：{username}")
    except Exception as e:
        print("❌ 錯誤：", e)

if __name__ == "__main__":
    main()
