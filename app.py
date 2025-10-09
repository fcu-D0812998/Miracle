import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from login_page import login_page
from db_config import get_connection

st.set_page_config(page_title="印表機記帳平台 - Dashboard", page_icon="📊", layout="wide")

# 檢查是否已登入
if "user" not in st.session_state:
    login_page()
    st.stop()

user = st.session_state["user"]

# 側邊欄
st.sidebar.success(f"👤 使用者：{user['username']}")

if st.sidebar.button("登出"):
    st.session_state.clear()
    st.rerun()

# ============================================
# Dashboard 首頁
# ============================================
st.title("📊 Dashboard - 營運總覽")

# ============================================
# 核心指標（客戶要求的三大指標）
# ============================================
st.subheader("🎯 核心營運指標")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1️⃣ 目前總台數
            cur.execute("SELECT COUNT(*) FROM devices")
            total_devices = cur.fetchone()[0]
            
            # 2️⃣ 總租金（所有設備的月租金總和）
            cur.execute("SELECT COALESCE(SUM(monthly_rent), 0) FROM devices")
            total_monthly_rent = cur.fetchone()[0]
            
            # 3️⃣ 近一年營利（收入 - 支出）
            one_year_ago = datetime.now() - timedelta(days=365)
            
            # 近一年總收入（發票）
            cur.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM invoices 
                WHERE date >= %s
            """, (one_year_ago.date(),))
            total_income = cur.fetchone()[0]
            
            # 近一年總支出
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM expenses 
                WHERE date >= %s
            """, (one_year_ago.date(),))
            total_expense = cur.fetchone()[0]
            
            # 計算營利
            yearly_profit = total_income - total_expense

    # 顯示核心指標
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="🖨️ 目前總台數",
            value=f"{total_devices} 台",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💰 總租金（月）",
            value=f"NT$ {total_monthly_rent:,.0f}",
            delta=None
        )
    
    with col3:
        profit_color = "normal" if yearly_profit >= 0 else "inverse"
        st.metric(
            label="📈 近一年營利",
            value=f"NT$ {yearly_profit:,.0f}",
            delta=f"收入 {total_income:,.0f} - 支出 {total_expense:,.0f}"
        )
    
except Exception as e:
    st.error(f"❌ 無法載入核心指標：{e}")

# ============================================
# 次要統計指標
# ============================================
st.divider()
st.subheader("📋 次要統計")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 客戶總數
            cur.execute("SELECT COUNT(*) FROM customers WHERE status = 'ACTIVE'")
            active_customers = cur.fetchone()[0]
            
            # 進行中合約
            cur.execute("SELECT COUNT(*) FROM contracts WHERE status = 'ACTIVE'")
            active_contracts = cur.fetchone()[0]
            
            # 未收發票數
            cur.execute("SELECT COUNT(*) FROM invoices WHERE status = 'OPEN'")
            open_invoices = cur.fetchone()[0]
            
            # 應收帳款總額
            cur.execute("SELECT COALESCE(SUM(open_amount), 0) FROM v_invoice_balance")
            total_ar = cur.fetchone()[0]
            
            # 本月收款
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM payments 
                WHERE EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)
                  AND EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM CURRENT_DATE)
            """)
            monthly_payment = cur.fetchone()[0]
            
            # 本月支出
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) 
                FROM expenses 
                WHERE EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)
                  AND EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM CURRENT_DATE)
            """)
            monthly_expense = cur.fetchone()[0]

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 活躍客戶", f"{active_customers} 家")
        st.metric("📄 進行中合約", f"{active_contracts} 筆")
    
    with col2:
        st.metric("🧾 未收發票", f"{open_invoices} 張")
        st.metric("💳 應收帳款", f"NT$ {total_ar:,.0f}")
    
    with col3:
        st.metric("💵 本月收款", f"NT$ {monthly_payment:,.0f}")
        st.metric("💸 本月支出", f"NT$ {monthly_expense:,.0f}")
    
except Exception as e:
    st.error(f"❌ 無法載入次要統計：{e}")

# ============================================
# 近期活動
# ============================================
st.divider()
st.subheader("📅 近期活動")

tab1, tab2, tab3 = st.tabs(["最近發票", "最近收款", "最近支出"])

with tab1:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        i.invoice_no,
                        cu.name,
                        i.date,
                        i.total,
                        i.status
                    FROM invoices i
                    JOIN customers cu ON i.customer_id = cu.id
                    ORDER BY i.date DESC
                    LIMIT 10
                """)
                recent_invoices = cur.fetchall()
        
        if recent_invoices:
            df = pd.DataFrame(recent_invoices, columns=["發票號碼", "客戶", "日期", "金額", "狀態"])
            df["金額"] = df["金額"].apply(lambda x: f"NT$ {x:,.0f}")
            df["狀態"] = df["狀態"].map({"OPEN": "🔴 未收", "PAID": "🟢 已收", "PARTIAL": "🟡 部分"})
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前無發票資料")
    except Exception as e:
        st.error(f"❌ 載入失敗：{e}")

with tab2:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        cu.name,
                        p.date,
                        p.amount,
                        p.method
                    FROM payments p
                    JOIN customers cu ON p.customer_id = cu.id
                    ORDER BY p.date DESC
                    LIMIT 10
                """)
                recent_payments = cur.fetchall()
        
        if recent_payments:
            df = pd.DataFrame(recent_payments, columns=["客戶", "日期", "金額", "方式"])
            df["金額"] = df["金額"].apply(lambda x: f"NT$ {x:,.0f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前無收款資料")
    except Exception as e:
        st.error(f"❌ 載入失敗：{e}")

with tab3:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        date,
                        type,
                        amount,
                        vendor
                    FROM expenses
                    ORDER BY date DESC
                    LIMIT 10
                """)
                recent_expenses = cur.fetchall()
        
        if recent_expenses:
            df = pd.DataFrame(recent_expenses, columns=["日期", "類型", "金額", "廠商"])
            df["金額"] = df["金額"].apply(lambda x: f"NT$ {x:,.0f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前無支出資料")
    except Exception as e:
        st.error(f"❌ 載入失敗：{e}")

# ============================================
# 頁尾提示
# ============================================
st.divider()
st.info("💡 提示：請使用左側選單切換至各功能頁面進行詳細操作。")
