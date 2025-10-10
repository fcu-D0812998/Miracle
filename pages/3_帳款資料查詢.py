import streamlit as st
from db_config import get_connection
import pandas as pd
from datetime import date

st.set_page_config(page_title="帳款資料查詢", page_icon="💰", layout="wide")

st.title("💰 帳款資料查詢")

# ============================================
# 編輯應收帳款 Dialog
# ============================================
@st.dialog("編輯應收帳款", width="large")
def edit_ar_dialog(ar_data):
    """編輯應收帳款（僅手續費、已收金額、繳費狀況）"""
    
    with st.form("edit_ar_form"):
        st.write(f"**合約編號：** {ar_data['contract_code']}")
        st.write(f"**客戶名稱：** {ar_data['customer_name']}")
        st.write(f"**類型：** {ar_data['type']}")
        
        st.divider()
        
        # 可編輯欄位
        fee = st.number_input(
            "手續費",
            min_value=0.0,
            value=float(ar_data['fee']) if ar_data['fee'] else 0.0,
            step=100.0
        )
        
        received_amount = st.number_input(
            "已收金額",
            min_value=0.0,
            value=float(ar_data['received_amount']) if ar_data['received_amount'] else 0.0,
            step=100.0
        )
        
        payment_status = st.selectbox(
            "繳費狀況",
            options=['未收', '部分收款', '已收款'],
            index=['未收', '部分收款', '已收款'].index(ar_data['payment_status']) if ar_data['payment_status'] in ['未收', '部分收款', '已收款'] else 0
        )
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        # 根據類型更新不同的表
                        if ar_data['type'] == '租賃':
                            cur.execute("""
                                UPDATE ar_leasing 
                                SET fee = %s, received_amount = %s, payment_status = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, (fee, received_amount, payment_status, ar_data['id']))
                        else:  # 買斷
                            cur.execute("""
                                UPDATE ar_buyout 
                                SET fee = %s, received_amount = %s, payment_status = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, (fee, received_amount, payment_status, ar_data['id']))
                        
                        conn.commit()
                st.success("✅ 應收帳款更新成功！")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 日期選擇器和篩選選項
# ============================================
col_date, col_type, col_search = st.columns([1, 1, 2])

with col_date:
    selected_date = st.date_input(
        "選擇日期（篩選年月）",
        value=date.today(),
        key="date_selector"
    )

# 取得選擇的年月
selected_year = selected_date.year
selected_month = selected_date.month

with col_type:
    ar_type = st.selectbox(
        "帳款類型",
        options=["總應收帳款", "總未收帳款"],
        key="ar_type_select"
    )

# ============================================
# 搜尋功能
# ============================================
with col_search:
    search_term = st.text_input(
        "🔍 搜尋帳款（可搜尋任何欄位）", 
        placeholder="輸入合約編號、客戶名稱等...", 
        label_visibility="collapsed"
    )

st.divider()

# ============================================
# 載入帳款資料
# ============================================
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查詢租賃應收帳款（篩選年月）
            cur.execute("""
                SELECT 
                    id,
                    '租賃' as type,
                    contract_code,
                    customer_code,
                    customer_name,
                    start_date as date,
                    end_date,
                    total_rent as amount,
                    fee,
                    received_amount,
                    payment_status
                FROM ar_leasing
                WHERE EXTRACT(YEAR FROM start_date) = %s 
                  AND EXTRACT(MONTH FROM start_date) = %s
            """, (selected_year, selected_month))
            leasing_data = cur.fetchall()
            
            # 查詢買斷應收帳款（篩選年月）
            cur.execute("""
                SELECT 
                    id,
                    '買斷' as type,
                    contract_code,
                    customer_code,
                    customer_name,
                    deal_date as date,
                    NULL as end_date,
                    total_amount as amount,
                    fee,
                    received_amount,
                    payment_status
                FROM ar_buyout
                WHERE EXTRACT(YEAR FROM deal_date) = %s 
                  AND EXTRACT(MONTH FROM deal_date) = %s
            """, (selected_year, selected_month))
            buyout_data = cur.fetchall()
    
    # 合併資料
    all_data = leasing_data + buyout_data
    
    if not all_data:
        st.info(f"📝 {selected_year}年{selected_month}月 沒有帳款資料")
    else:
        # 轉換為 DataFrame
        columns = ['id', 'type', 'contract_code', 'customer_code', 'customer_name', 'date', 
                   'end_date', 'amount', 'fee', 'received_amount', 'payment_status']
        df = pd.DataFrame(all_data, columns=columns)
        
        # 按合約編號排序
        df = df.sort_values('contract_code')
        
        # 根據選擇的帳款類型篩選資料
        if ar_type == "總未收帳款":
            # 篩選繳費狀況不是「已收款」的資料
            df = df[df['payment_status'] != '已收款']
        
        # 計算匯總數字
        if ar_type == "總應收帳款":
            # 總應收金額和總手續費
            total_amount = df['amount'].sum()
            total_fee = df['fee'].sum()
            
            # 顯示匯總資訊
            st.subheader(f"📊 {selected_year}年{selected_month}月 總應收帳款")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="💰 總應收金額",
                    value=f"NT$ {total_amount:,.0f}"
                )
            
            with col2:
                st.metric(
                    label="📋 總手續費",
                    value=f"NT$ {total_fee:,.0f}"
                )
        else:  # 總未收帳款
            # 計算實際未收金額 = SUM((金額 + 手續費) - 已收金額)
            df['unpaid_amount'] = (df['amount'].fillna(0) + df['fee'].fillna(0)) - df['received_amount'].fillna(0)
            total_unpaid = df['unpaid_amount'].sum()
            
            # 顯示匯總資訊
            st.subheader(f"📊 {selected_year}年{selected_month}月 總未收帳款")
            st.metric(
                label="💰 總未收金額",
                value=f"NT$ {total_unpaid:,.0f}"
            )
        
        st.divider()
        
        # 搜尋功能
        if search_term:
            mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
            df = df[mask]
        
        if len(df) == 0:
            st.warning(f"🔍 找不到符合 '{search_term}' 的帳款資料")
        else:
            st.write(f"共 {len(df)} 筆帳款資料")
            
            # 顯示每一筆帳款
            for idx, row in df.iterrows():
                with st.container(border=True):
                    # 主要資訊顯示
                    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([0.8, 1.5, 1.5, 1, 1.2, 1, 1, 1, 0.6])
                    
                    with col1:
                        st.write(f"**類型**")
                        # 使用不同顏色標籤
                        if row['type'] == '租賃':
                            st.markdown("🔵 租賃")
                        else:
                            st.markdown("🟢 買斷")
                    
                    with col2:
                        st.write(f"**合約編號**")
                        st.write(row['contract_code'])
                    
                    with col3:
                        st.write(f"**客戶名稱**")
                        st.write(row['customer_name'])
                    
                    with col4:
                        st.write(f"**日期**")
                        st.write(row['date'].strftime('%Y-%m-%d') if row['date'] else "-")
                    
                    with col5:
                        st.write(f"**金額**")
                        st.write(f"NT$ {row['amount']:,.0f}" if row['amount'] else "-")
                    
                    with col6:
                        st.write(f"**手續費**")
                        st.write(f"NT$ {row['fee']:,.0f}" if row['fee'] else "-")
                    
                    with col7:
                        st.write(f"**已收金額**")
                        st.write(f"NT$ {row['received_amount']:,.0f}" if row['received_amount'] else "-")
                    
                    with col8:
                        st.write(f"**繳費狀況**")
                        # 根據繳費狀況顯示不同顏色
                        status = row['payment_status']
                        if status == '未收':
                            st.markdown("🔴 未收")
                        elif status == '部分收款':
                            st.markdown("🟡 部分收款")
                        elif status == '已收款':
                            st.markdown("🟢 已收款")
                        else:
                            st.write(status if status else "-")
                    
                    with col9:
                        # 編輯按鈕
                        if st.button("✏️", key=f"edit_{row['type']}_{row['id']}", help="編輯"):
                            edit_ar_dialog(row.to_dict())
                    
                    # 詳細資料展開
                    with st.expander("📋 查看詳細資料"):
                        col_detail1, col_detail2 = st.columns(2)
                        
                        with col_detail1:
                            st.write(f"**客戶代碼：** {row['customer_code'] if row['customer_code'] else '-'}")
                            if row['type'] == '租賃':
                                st.write(f"**起始日期：** {row['date'].strftime('%Y-%m-%d') if row['date'] else '-'}")
                                st.write(f"**結束日期：** {row['end_date'].strftime('%Y-%m-%d') if row['end_date'] else '-'}")
                            else:
                                st.write(f"**成交日期：** {row['date'].strftime('%Y-%m-%d') if row['date'] else '-'}")
                        
                        with col_detail2:
                            # 計算應收總額（金額+手續費）
                            total_receivable = (row['amount'] if row['amount'] else 0) + (row['fee'] if row['fee'] else 0)
                            # 計算未收金額
                            unpaid = total_receivable - (row['received_amount'] if row['received_amount'] else 0)
                            
                            st.write(f"**應收總額：** NT$ {total_receivable:,.0f}")
                            st.write(f"**未收金額：** NT$ {unpaid:,.0f}")

except Exception as e:
    st.error(f"❌ 載入帳款資料失敗：{e}")

