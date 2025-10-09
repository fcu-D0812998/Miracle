import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from db_config import get_connection

# 設定頁面
st.set_page_config(page_title="帳款資料查詢", page_icon="💰", layout="wide")

# 檢查登入狀態
if "user" not in st.session_state:
    st.error("❌ 請先登入")
    st.stop()

st.title("💰 帳款資料查詢")

# ============================================
# 輔助函數
# ============================================

def should_charge_this_month(start_date, pay_mode_months, check_date=None):
    """判斷指定日期是否為應收月份"""
    if check_date is None:
        check_date = date.today()
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # 計算月份差
    months_diff = (check_date.year - start_date.year) * 12 + (check_date.month - start_date.month)
    
    # 如果月份差能被繳費模式整除，則為應收月份
    return months_diff >= 0 and months_diff % pay_mode_months == 0

def get_next_due_date(start_date, pay_mode_months):
    """計算下次應收日期"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    current_date = date.today()
    months_diff = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
    
    # 計算下一個應收週期
    next_period = ((months_diff // pay_mode_months) + 1) * pay_mode_months
    next_due = start_date + relativedelta(months=next_period)
    
    return next_due

# ============================================
# 1️⃣ 總應收帳款（當月應收）
# ============================================
st.subheader("📊 總應收帳款（當月應收）")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 載入所有進行中的合約
            cur.execute("""
                SELECT 
                    c.id AS contract_id,
                    cu.code AS customer_code,
                    cu.name AS customer_name,
                    c.start_date,
                    c.pay_mode_months,
                    c.model,
                    c.status
                FROM contracts c
                JOIN customers cu ON c.customer_id = cu.id
                WHERE c.status = 'ACTIVE'
                ORDER BY cu.code
            """)
            contracts = cur.fetchall()
    
    # 篩選當月應收的合約
    current_month_ar = []
    total_ar_amount = 0
    
    for contract in contracts:
        contract_id, cust_code, cust_name, start_date, pay_mode, model, status = contract
        
        # 判斷當月是否應收
        if should_charge_this_month(start_date, pay_mode):
            # 計算該合約的月租金總額
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(SUM(monthly_rent), 0)
                        FROM devices
                        WHERE contract_id = %s
                    """, (contract_id,))
                    monthly_rent = cur.fetchone()[0]
            
            # 應收金額 = 月租金 × 繳費模式
            due_amount = monthly_rent * pay_mode
            total_ar_amount += due_amount
            
            # 計算下次應收日期
            next_due = get_next_due_date(start_date, pay_mode)
            
            current_month_ar.append({
                "合約編號": contract_id,
                "客戶代碼": cust_code,
                "客戶名稱": cust_name,
                "機型": model or "-",
                "合約起始日": start_date,
                "繳費模式": f"{pay_mode} 月繳",
                "本期應收日": date.today().replace(day=1),
                "下期應收日": next_due,
                "月租金": f"NT$ {monthly_rent:,.0f}",
                "應收金額": f"NT$ {due_amount:,.0f}"
            })
    
    if current_month_ar:
        df_ar = pd.DataFrame(current_month_ar)
        st.dataframe(df_ar, use_container_width=True, hide_index=True)
        
        # 統計
        col1, col2 = st.columns(2)
        col1.metric("本月應收合約數", len(current_month_ar))
        col2.metric("本月應收總額", f"NT$ {total_ar_amount:,.0f}")
    else:
        st.info("本月無應收帳款")

except Exception as e:
    st.error(f"❌ 載入總應收帳款失敗：{e}")

# ============================================
# 2️⃣ 總未收帳款
# ============================================
st.divider()
st.subheader("📊 總未收帳款")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.id,
                    cu.code AS customer_code,
                    cu.name AS customer_name,
                    i.invoice_no,
                    i.date,
                    i.total,
                    COALESCE(SUM(pa.applied_amount), 0) AS paid_amount,
                    COALESCE(SUM(p.fee_amount), 0) AS total_fee
                FROM invoices i
                JOIN customers cu ON i.customer_id = cu.id
                LEFT JOIN payment_allocations pa ON i.id = pa.invoice_id
                LEFT JOIN payments p ON pa.payment_id = p.id
                WHERE i.status IN ('OPEN', 'PARTIAL')
                GROUP BY i.id, cu.code, cu.name, i.invoice_no, i.date, i.total
                ORDER BY i.date DESC
            """)
            unpaid_invoices = cur.fetchall()
    
    if unpaid_invoices:
        unpaid_data = []
        total_unpaid = 0
        
        for invoice in unpaid_invoices:
            inv_id, cust_code, cust_name, inv_no, inv_date, total, paid, fee = invoice
            unpaid_amount = total - paid
            total_unpaid += unpaid_amount
            
            unpaid_data.append({
                "發票編號": inv_id,
                "客戶代碼": cust_code,
                "客戶名稱": cust_name,
                "發票號碼": inv_no,
                "發票日期": inv_date,
                "發票金額": f"NT$ {total:,.0f}",
                "已收金額": f"NT$ {paid:,.0f}",
                "手續費": f"NT$ {fee:,.0f}",
                "未收金額": f"NT$ {unpaid_amount:,.0f}"
            })
        
        df_unpaid = pd.DataFrame(unpaid_data)
        st.dataframe(df_unpaid, use_container_width=True, hide_index=True)
        
        # 統計
        col1, col2 = st.columns(2)
        col1.metric("未收發票數", len(unpaid_data))
        col2.metric("未收總額", f"NT$ {total_unpaid:,.0f}")
    else:
        st.info("目前無未收帳款")

except Exception as e:
    st.error(f"❌ 載入總未收帳款失敗：{e}")

# ============================================
# 3️⃣ 未出帳款
# ============================================
st.divider()
st.subheader("📊 未出帳款")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    pc.id,
                    cu.code AS customer_code,
                    cu.name AS customer_name,
                    pc.contract_id,
                    pc.charge_type,
                    pc.qty,
                    pc.rate,
                    pc.amount,
                    pc.period_start,
                    pc.period_end,
                    pc.note
                FROM pending_charges pc
                JOIN contracts c ON pc.contract_id = c.id
                JOIN customers cu ON c.customer_id = cu.id
                WHERE pc.status = 'PENDING'
                ORDER BY COALESCE(pc.period_start, CURRENT_DATE) DESC, cu.code
            """)
            pending = cur.fetchall()
    
    if pending:
        pending_data = []
        total_pending = 0
        
        for charge in pending:
            pc_id, cust_code, cust_name, contract_id, charge_type, qty, rate, amount, period_start, period_end, note = charge
            total_pending += amount
            
            charge_type_map = {
                'BASE': '基本租金',
                'OVERAGE': '超量費用',
                'SERVICE': '服務費用',
                'MISC_PASS': '其他代付'
            }
            
            # 格式化期間
            if period_start and period_end:
                period_str = f"{period_start} ~ {period_end}"
            elif period_start:
                period_str = str(period_start)
            else:
                period_str = "-"
            
            pending_data.append({
                "編號": pc_id,
                "客戶代碼": cust_code,
                "客戶名稱": cust_name,
                "合約編號": contract_id,
                "費用類型": charge_type_map.get(charge_type, charge_type),
                "數量": qty,
                "單價": f"NT$ {rate:,.2f}",
                "金額": f"NT$ {amount:,.0f}",
                "期間": period_str,
                "備註": note or "-"
            })
        
        df_pending = pd.DataFrame(pending_data)
        st.dataframe(df_pending, use_container_width=True, hide_index=True)
        
        # 統計
        col1, col2 = st.columns(2)
        col1.metric("未出帳筆數", len(pending_data))
        col2.metric("未出帳總額", f"NT$ {total_pending:,.0f}")
    else:
        st.info("目前無未出帳款")

except Exception as e:
    st.error(f"❌ 載入未出帳款失敗：{e}")

# ============================================
# 4️⃣ 已出帳款
# ============================================
st.divider()
st.subheader("📊 已出帳款")

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.id,
                    cu.code AS customer_code,
                    cu.name AS customer_name,
                    i.invoice_no,
                    i.date,
                    i.period_start,
                    i.period_end,
                    i.total,
                    i.status
                FROM invoices i
                JOIN customers cu ON i.customer_id = cu.id
                ORDER BY i.date DESC
                LIMIT 100
            """)
            invoices = cur.fetchall()
    
    if invoices:
        invoice_data = []
        
        status_map = {
            'OPEN': '🔴 未收',
            'PAID': '🟢 已收',
            'PARTIAL': '🟡 部分收款'
        }
        
        for invoice in invoices:
            inv_id, cust_code, cust_name, inv_no, inv_date, period_start, period_end, total, status = invoice
            
            invoice_data.append({
                "發票編號": inv_id,
                "客戶代碼": cust_code,
                "客戶名稱": cust_name,
                "發票號碼": inv_no,
                "發票日期": inv_date,
                "期間起": period_start or "-",
                "期間迄": period_end or "-",
                "金額": f"NT$ {total:,.0f}",
                "狀態": status_map.get(status, status)
            })
        
        df_invoices = pd.DataFrame(invoice_data)
        st.dataframe(df_invoices, use_container_width=True, hide_index=True)
        
        st.info(f"💡 顯示最近 100 筆發票，共 {len(invoice_data)} 筆")
    else:
        st.info("目前無已出帳款")

except Exception as e:
    st.error(f"❌ 載入已出帳款失敗：{e}")

# ============================================
# 5️⃣ 日期金額查詢
# ============================================
st.divider()
st.subheader("🔍 日期金額查詢")

with st.form("search_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        search_start_date = st.date_input("起始日期", value=date.today().replace(day=1))
        search_end_date = st.date_input("結束日期", value=date.today())
        
        # 載入客戶列表
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, code, name FROM customers WHERE status = 'ACTIVE' ORDER BY code")
                    customers = cur.fetchall()
            
            customer_options = {"（全部客戶）": None}
            customer_options.update({f"{code} - {name}": cid for cid, code, name in customers})
            search_customer = st.selectbox("客戶", list(customer_options.keys()))
        except Exception as e:
            st.error(f"❌ 載入客戶列表失敗：{e}")
            customer_options = {"（全部客戶）": None}
            search_customer = "（全部客戶）"
    
    with col2:
        search_min_amount = st.number_input("最小金額", min_value=0.0, value=0.0, step=1000.0)
        search_max_amount = st.number_input("最大金額（0 = 不限）", min_value=0.0, value=0.0, step=1000.0)
    
    submitted = st.form_submit_button("🔍 查詢", type="primary", use_container_width=True)
    
    if submitted:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 建立查詢條件
                    query = """
                        SELECT 
                            i.id,
                            cu.code AS customer_code,
                            cu.name AS customer_name,
                            i.invoice_no,
                            i.date,
                            i.total,
                            i.status
                        FROM invoices i
                        JOIN customers cu ON i.customer_id = cu.id
                        WHERE i.date BETWEEN %s AND %s
                    """
                    params = [search_start_date, search_end_date]
                    
                    # 客戶條件
                    if customer_options[search_customer] is not None:
                        query += " AND i.customer_id = %s"
                        params.append(customer_options[search_customer])
                    
                    # 金額條件
                    if search_min_amount > 0:
                        query += " AND i.total >= %s"
                        params.append(search_min_amount)
                    
                    if search_max_amount > 0:
                        query += " AND i.total <= %s"
                        params.append(search_max_amount)
                    
                    query += " ORDER BY i.date DESC"
                    
                    cur.execute(query, params)
                    search_results = cur.fetchall()
            
            if search_results:
                search_data = []
                total_search_amount = 0
                
                status_map = {
                    'OPEN': '🔴 未收',
                    'PAID': '🟢 已收',
                    'PARTIAL': '🟡 部分收款'
                }
                
                for result in search_results:
                    inv_id, cust_code, cust_name, inv_no, inv_date, total, status = result
                    total_search_amount += total
                    
                    search_data.append({
                        "發票編號": inv_id,
                        "客戶代碼": cust_code,
                        "客戶名稱": cust_name,
                        "發票號碼": inv_no,
                        "日期": inv_date,
                        "金額": f"NT$ {total:,.0f}",
                        "狀態": status_map.get(status, status)
                    })
                
                st.success(f"✅ 查詢到 {len(search_data)} 筆記錄")
                
                df_search = pd.DataFrame(search_data)
                st.dataframe(df_search, use_container_width=True, hide_index=True)
                
                # 統計
                col1, col2 = st.columns(2)
                col1.metric("查詢筆數", len(search_data))
                col2.metric("查詢總額", f"NT$ {total_search_amount:,.0f}")
            else:
                st.warning("⚠️ 查無符合條件的記錄")
        
        except Exception as e:
            st.error(f"❌ 查詢失敗：{e}")

# ============================================
# 頁尾提示
# ============================================
st.divider()
st.info("💡 提示：總應收帳款會根據合約起始日與繳費模式自動計算當月應收項目。")
