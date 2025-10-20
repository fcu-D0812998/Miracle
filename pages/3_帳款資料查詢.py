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
# 編輯未出帳款 Dialog
# ============================================
@st.dialog("編輯未出帳款", width="large")
def edit_payable_dialog(payable_data):
    """編輯未出帳款（僅付款狀態）"""
    
    with st.form("edit_payable_form"):
        st.write(f"**合約編號：** {payable_data['contract_code']}")
        st.write(f"**客戶名稱：** {payable_data['customer_name']}")
        st.write(f"**類型：** {payable_data['contract_type']}")
        st.write(f"**付款對象：** {payable_data['payable_type']}")
        st.write(f"**公司代碼：** {payable_data['company_code']}")
        st.write(f"**金額：** NT$ {payable_data['amount']:,.0f}")
        
        st.divider()
        
        # 可編輯欄位：付款狀態
        payment_status = st.selectbox(
            "付款狀況",
            options=['未付款', '部分付款', '已付款'],
            index=['未付款', '部分付款', '已付款'].index(payable_data['payment_status']) if payable_data['payment_status'] in ['未付款', '部分付款', '已付款'] else 0
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
                        # 根據合約類型和付款對象更新不同的欄位
                        if payable_data['contract_type'] == '租賃':
                            if payable_data['payable_type'] == '業務':
                                cur.execute("""
                                    UPDATE contracts_leasing 
                                    SET sales_payment_status = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE contract_code = %s
                                """, (payment_status, payable_data['contract_code']))
                            else:  # 維護
                                cur.execute("""
                                    UPDATE contracts_leasing 
                                    SET service_payment_status = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE contract_code = %s
                                """, (payment_status, payable_data['contract_code']))
                        else:  # 買斷
                            if payable_data['payable_type'] == '業務':
                                cur.execute("""
                                    UPDATE contracts_buyout 
                                    SET sales_payment_status = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE contract_code = %s
                                """, (payment_status, payable_data['contract_code']))
                            else:  # 維護
                                cur.execute("""
                                    UPDATE contracts_buyout 
                                    SET service_payment_status = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE contract_code = %s
                                """, (payment_status, payable_data['contract_code']))
                        
                        conn.commit()
                st.success("✅ 付款狀態更新成功！")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 搜尋功能（最上方）
# ============================================
search_term = st.text_input(
    "🔍 搜尋帳款（可搜尋任何欄位）", 
    placeholder="輸入合約編號、客戶名稱等...", 
    label_visibility="collapsed"
)

st.divider()

# ============================================
# 日期選擇器和篩選選項
# ============================================
col_date_from, col_date_to, col_type = st.columns([1, 1, 1])

with col_date_from:
    from_date = st.date_input(
        "起始日期",
        value=date(date.today().year, date.today().month, 1),  # 本月第一天
        key="from_date_selector"
    )

with col_date_to:
    to_date = st.date_input(
        "結束日期",
        value=date.today(),
        key="to_date_selector"
    )

with col_type:
    ar_type = st.selectbox(
        "帳款類型",
        options=["總應收帳款", "總未收帳款", "未出帳款", "已出帳款"],
        key="ar_type_select"
    )

st.divider()

# ============================================
# 載入帳款資料
# ============================================
try:
    # 根據選擇的帳款類型查詢不同的資料
    if ar_type == "未出帳款":
        # 查詢未出帳款（應付帳款 - 未付款）
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃合約的未出帳款（業務）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '租賃' as contract_type,
                        customer_code,
                        customer_name,
                        start_date as date,
                        '業務' as payable_type,
                        sales_company_code as company_code,
                        sales_amount as amount,
                        sales_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND sales_payment_status != '已付款'
                      AND sales_amount > 0
                """, (from_date, to_date))
                leasing_sales_data = cur.fetchall()
                
                # 查詢租賃合約的未出帳款（維護）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '租賃' as contract_type,
                        customer_code,
                        customer_name,
                        start_date as date,
                        '維護' as payable_type,
                        service_company_code as company_code,
                        service_amount as amount,
                        service_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND service_payment_status != '已付款'
                      AND service_amount > 0
                """, (from_date, to_date))
                leasing_service_data = cur.fetchall()
                
                # 查詢買斷合約的未出帳款（業務）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '買斷' as contract_type,
                        customer_code,
                        customer_name,
                        deal_date as date,
                        '業務' as payable_type,
                        sales_company_code as company_code,
                        sales_amount as amount,
                        sales_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND sales_payment_status != '已付款'
                      AND sales_amount > 0
                """, (from_date, to_date))
                buyout_sales_data = cur.fetchall()
                
                # 查詢買斷合約的未出帳款（維護）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '買斷' as contract_type,
                        customer_code,
                        customer_name,
                        deal_date as date,
                        '維護' as payable_type,
                        service_company_code as company_code,
                        service_amount as amount,
                        service_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND service_payment_status != '已付款'
                      AND service_amount > 0
                """, (from_date, to_date))
                buyout_service_data = cur.fetchall()
        
        # 合併所有未出帳款資料
        all_data = leasing_sales_data + leasing_service_data + buyout_sales_data + buyout_service_data
    
    elif ar_type == "已出帳款":
        # 查詢已出帳款（應付帳款 - 已付款）
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃合約的已出帳款（業務）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '租賃' as contract_type,
                        customer_code,
                        customer_name,
                        start_date as date,
                        '業務' as payable_type,
                        sales_company_code as company_code,
                        sales_amount as amount,
                        sales_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND sales_payment_status = '已付款'
                      AND sales_amount > 0
                """, (from_date, to_date))
                leasing_sales_data = cur.fetchall()
                
                # 查詢租賃合約的已出帳款（維護）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '租賃' as contract_type,
                        customer_code,
                        customer_name,
                        start_date as date,
                        '維護' as payable_type,
                        service_company_code as company_code,
                        service_amount as amount,
                        service_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND service_payment_status = '已付款'
                      AND service_amount > 0
                """, (from_date, to_date))
                leasing_service_data = cur.fetchall()
                
                # 查詢買斷合約的已出帳款（業務）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '買斷' as contract_type,
                        customer_code,
                        customer_name,
                        deal_date as date,
                        '業務' as payable_type,
                        sales_company_code as company_code,
                        sales_amount as amount,
                        sales_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND sales_payment_status = '已付款'
                      AND sales_amount > 0
                """, (from_date, to_date))
                buyout_sales_data = cur.fetchall()
                
                # 查詢買斷合約的已出帳款（維護）
                cur.execute("""
                    SELECT 
                        contract_code,
                        '買斷' as contract_type,
                        customer_code,
                        customer_name,
                        deal_date as date,
                        '維護' as payable_type,
                        service_company_code as company_code,
                        service_amount as amount,
                        service_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND service_payment_status = '已付款'
                      AND service_amount > 0
                """, (from_date, to_date))
                buyout_service_data = cur.fetchall()
        
        # 合併所有已出帳款資料
        all_data = leasing_sales_data + leasing_service_data + buyout_sales_data + buyout_service_data
    else:
        # 查詢應收帳款
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃應收帳款（篩選日期區間）
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
                    WHERE start_date BETWEEN %s AND %s
                """, (from_date, to_date))
                leasing_data = cur.fetchall()
                
                # 查詢買斷應收帳款（篩選日期區間）
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
                    WHERE deal_date BETWEEN %s AND %s
                """, (from_date, to_date))
                buyout_data = cur.fetchall()
        
        # 合併資料
        all_data = leasing_data + buyout_data
    
    if not all_data:
        st.info(f"📝 {from_date.strftime('%Y-%m-%d')} ~ {to_date.strftime('%Y-%m-%d')} 沒有帳款資料")
    else:
        # 根據帳款類型處理不同的資料結構
        if ar_type == "未出帳款" or ar_type == "已出帳款":
            # 未出/已出帳款資料結構
            columns = ['contract_code', 'contract_type', 'customer_code', 'customer_name', 'date',
                      'payable_type', 'company_code', 'amount', 'payment_status']
            df = pd.DataFrame(all_data, columns=columns)
            
            # 按合約編號排序
            df = df.sort_values('contract_code')
            
            # 計算總金額
            total_payable = df['amount'].sum()
            
            # 顯示匯總資訊
            if ar_type == "未出帳款":
                st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 未出帳款")
                st.metric(
                    label="💰 總未出帳款金額",
                    value=f"NT$ {total_payable:,.0f}"
                )
            else:  # 已出帳款
                st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 已出帳款")
                st.metric(
                    label="💰 總已出帳款金額",
                    value=f"NT$ {total_payable:,.0f}"
                )
        else:
            # 應收帳款資料結構
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
                st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 總應收帳款")
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
                st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 總未收帳款")
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
            
            # 編輯按鈕（表格上方）
            col_edit, col_space = st.columns([1, 9])
            
            with col_edit:
                if ar_type in ["未出帳款", "已出帳款"]:
                    # 未出/已出帳款編輯按鈕
                    if st.button("✏️ 編輯帳款", use_container_width=True, key="edit_payable_btn"):
                        # 檢查是否有選擇資料
                        if 'selected_payable_idx' in st.session_state and st.session_state['selected_payable_idx'] is not None:
                            selected_idx = st.session_state['selected_payable_idx']
                            if selected_idx < len(df):
                                selected_row = df.iloc[selected_idx]
                                edit_payable_dialog(selected_row.to_dict())
                            else:
                                st.warning("⚠️ 請先點選要編輯的帳款資料")
                        else:
                            st.warning("⚠️ 請先點選要編輯的帳款資料")
                else:
                    # 應收帳款編輯按鈕
                    if st.button("✏️ 編輯帳款", use_container_width=True, key="edit_ar_btn"):
                        # 檢查是否有選擇資料
                        if 'selected_ar_id' in st.session_state and st.session_state['selected_ar_id'] is not None:
                            selected_id = st.session_state['selected_ar_id']
                            selected_type = st.session_state['selected_ar_type']
                            if ((df['id'] == selected_id) & (df['type'] == selected_type)).any():
                                selected_row = df[(df['id'] == selected_id) & (df['type'] == selected_type)].iloc[0]
                                edit_ar_dialog(selected_row.to_dict())
                            else:
                                st.warning("⚠️ 請先點選要編輯的帳款資料")
                        else:
                            st.warning("⚠️ 請先點選要編輯的帳款資料")
            
            st.divider()
            
            # 根據帳款類型顯示不同的表格
            if ar_type in ["未出帳款", "已出帳款"]:
                # 未出/已出帳款表格
                display_df = df.copy()
                display_df = display_df.rename(columns={
                    'contract_code': '合約編號',
                    'contract_type': '類型',
                    'customer_code': '客戶代碼',
                    'customer_name': '客戶名稱',
                    'date': '日期',
                    'payable_type': '付款對象',
                    'company_code': '公司代碼',
                    'amount': '金額',
                    'payment_status': '付款狀況'
                })
                
                # 格式化日期和金額
                display_df['日期'] = display_df['日期'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '-')
                display_df['金額'] = display_df['金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                
                # 顯示表格
                selection = st.dataframe(
                    display_df[['合約編號', '類型', '客戶代碼', '客戶名稱', '日期', 
                               '付款對象', '公司代碼', '金額', '付款狀況']],
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="payable_table"
                )
                
                # 更新選擇狀態
                if selection and selection.selection.rows:
                    selected_idx = selection.selection.rows[0]
                    st.session_state['selected_payable_idx'] = selected_idx
                else:
                    st.session_state['selected_payable_idx'] = None
                
                # 顯示已選擇的資料
                if 'selected_payable_idx' in st.session_state and st.session_state['selected_payable_idx'] is not None:
                    selected_idx = st.session_state['selected_payable_idx']
                    if selected_idx < len(df):
                        selected_row = df.iloc[selected_idx]
                        st.info(f"✓ 已選擇：{selected_row['contract_code']} - {selected_row['customer_name']} ({selected_row['payable_type']})")
            
            else:
                # 應收帳款表格
                # 計算應收總額和未收金額欄位
                df['total_receivable'] = (df['amount'].fillna(0) + df['fee'].fillna(0))
                df['unpaid'] = df['total_receivable'] - df['received_amount'].fillna(0)
                
                # 準備顯示用的 DataFrame
                display_df = df.copy()
                display_df = display_df.rename(columns={
                    'type': '類型',
                    'contract_code': '合約編號',
                    'customer_code': '客戶代碼',
                    'customer_name': '客戶名稱',
                    'date': '日期',
                    'end_date': '結束日期',
                    'amount': '金額',
                    'fee': '手續費',
                    'received_amount': '已收金額',
                    'payment_status': '繳費狀況',
                    'total_receivable': '應收總額',
                    'unpaid': '未收金額'
                })
                
                # 格式化日期和金額
                display_df['日期'] = display_df['日期'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '-')
                display_df['結束日期'] = display_df['結束日期'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '-')
                display_df['金額'] = display_df['金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                display_df['手續費'] = display_df['手續費'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                display_df['已收金額'] = display_df['已收金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                display_df['應收總額'] = display_df['應收總額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                display_df['未收金額'] = display_df['未收金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) else '-')
                
                # 顯示表格
                selection = st.dataframe(
                    display_df[['類型', '合約編號', '客戶代碼', '客戶名稱', '日期', '結束日期', 
                               '金額', '手續費', '已收金額', '繳費狀況', '應收總額', '未收金額']],
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="ar_table"
                )
                
                # 更新選擇狀態
                if selection and selection.selection.rows:
                    selected_idx = selection.selection.rows[0]
                    selected_row = df.iloc[selected_idx]
                    st.session_state['selected_ar_id'] = selected_row['id']
                    st.session_state['selected_ar_type'] = selected_row['type']
                else:
                    st.session_state['selected_ar_id'] = None
                    st.session_state['selected_ar_type'] = None
                
                # 顯示已選擇的資料
                if 'selected_ar_id' in st.session_state and st.session_state['selected_ar_id'] is not None:
                    selected_id = st.session_state['selected_ar_id']
                    selected_type = st.session_state['selected_ar_type']
                    if ((df['id'] == selected_id) & (df['type'] == selected_type)).any():
                        selected_row = df[(df['id'] == selected_id) & (df['type'] == selected_type)].iloc[0]
                        st.info(f"✓ 已選擇：{selected_row['contract_code']} - {selected_row['customer_name']} ({selected_row['type']})")

except Exception as e:
    st.error(f"❌ 載入帳款資料失敗：{e}")

