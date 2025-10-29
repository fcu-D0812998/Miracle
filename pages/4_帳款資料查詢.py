import streamlit as st
from db_config import get_connection
import pandas as pd
from datetime import date, datetime
from io import BytesIO

st.set_page_config(page_title="帳款資料查詢", page_icon="💰", layout="wide")

st.title("💰 帳款資料查詢")

# ============================================
# 匯出 Excel 功能
# ============================================
def export_to_excel(from_date, to_date):
    """匯出所有四種帳款類型到 Excel（不同工作表）"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # ========== 查詢總應收帳款 ==========
                # 租賃應收
                cur.execute("""
                    SELECT '租賃' as type, contract_code, customer_code, customer_name,
                           start_date as date, end_date, total_rent as amount, fee,
                           received_amount, payment_status
                    FROM ar_leasing
                    WHERE start_date BETWEEN %s AND %s
                """, (from_date, to_date))
                ar_leasing = cur.fetchall()
                
                # 買斷應收
                cur.execute("""
                    SELECT '買斷' as type, contract_code, customer_code, customer_name,
                           deal_date as date, NULL as end_date, total_amount as amount, fee,
                           received_amount, payment_status
                    FROM ar_buyout
                    WHERE deal_date BETWEEN %s AND %s
                """, (from_date, to_date))
                ar_buyout = cur.fetchall()
                
                # 合併總應收帳款
                ar_columns = ['類型', '合約編號', '客戶代碼', '客戶名稱', '日期', '結束日期', 
                             '金額', '手續費', '已收金額', '繳費狀況']
                df_total_ar = pd.DataFrame(ar_leasing + ar_buyout, columns=ar_columns)
                df_total_ar['應收總額'] = df_total_ar['金額'] + df_total_ar['手續費']
                df_total_ar['未收金額'] = df_total_ar['應收總額'] - df_total_ar['已收金額']
                
                # 總未收帳款（篩選未收款）
                df_unpaid_ar = df_total_ar[df_total_ar['繳費狀況'] != '已收款'].copy()
                
                # ========== 查詢未出帳款 ==========
                # 租賃未出（業務+維護）
                cur.execute("""
                    SELECT contract_code, '租賃' as contract_type, customer_code, customer_name,
                           start_date as date, '業務' as payable_type, sales_company_code as company_code,
                           sales_amount as amount, sales_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND sales_payment_status != '已付款' AND sales_amount > 0
                    UNION ALL
                    SELECT contract_code, '租賃', customer_code, customer_name,
                           start_date, '維護', service_company_code,
                           service_amount, service_payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND service_payment_status != '已付款' AND service_amount > 0
                """, (from_date, to_date, from_date, to_date))
                unpaid_leasing = cur.fetchall()
                
                # 買斷未出（業務+維護）
                cur.execute("""
                    SELECT contract_code, '買斷' as contract_type, customer_code, customer_name,
                           deal_date as date, '業務' as payable_type, sales_company_code as company_code,
                           sales_amount as amount, sales_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND sales_payment_status != '已付款' AND sales_amount > 0
                    UNION ALL
                    SELECT contract_code, '買斷', customer_code, customer_name,
                           deal_date, '維護', service_company_code,
                           service_amount, service_payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND service_payment_status != '已付款' AND service_amount > 0
                """, (from_date, to_date, from_date, to_date))
                unpaid_buyout = cur.fetchall()
                
                payable_columns = ['合約編號', '類型', '客戶代碼', '客戶名稱', '日期', 
                                  '付款對象', '公司代碼', '金額', '付款狀況']
                df_unpaid_payable = pd.DataFrame(unpaid_leasing + unpaid_buyout, columns=payable_columns)
                
                # ========== 查詢已出帳款 ==========
                # 租賃已出（業務+維護）
                cur.execute("""
                    SELECT contract_code, '租賃' as contract_type, customer_code, customer_name,
                           start_date as date, '業務' as payable_type, sales_company_code as company_code,
                           sales_amount as amount, sales_payment_status as payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND sales_payment_status = '已付款' AND sales_amount > 0
                    UNION ALL
                    SELECT contract_code, '租賃', customer_code, customer_name,
                           start_date, '維護', service_company_code,
                           service_amount, service_payment_status
                    FROM contracts_leasing
                    WHERE start_date BETWEEN %s AND %s
                      AND service_payment_status = '已付款' AND service_amount > 0
                """, (from_date, to_date, from_date, to_date))
                paid_leasing = cur.fetchall()
                
                # 買斷已出（業務+維護）
                cur.execute("""
                    SELECT contract_code, '買斷' as contract_type, customer_code, customer_name,
                           deal_date as date, '業務' as payable_type, sales_company_code as company_code,
                           sales_amount as amount, sales_payment_status as payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND sales_payment_status = '已付款' AND sales_amount > 0
                    UNION ALL
                    SELECT contract_code, '買斷', customer_code, customer_name,
                           deal_date, '維護', service_company_code,
                           service_amount, service_payment_status
                    FROM contracts_buyout
                    WHERE deal_date BETWEEN %s AND %s
                      AND service_payment_status = '已付款' AND service_amount > 0
                """, (from_date, to_date, from_date, to_date))
                paid_buyout = cur.fetchall()
                
                df_paid_payable = pd.DataFrame(paid_leasing + paid_buyout, columns=payable_columns)
        
        # 創建 Excel 檔案
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_total_ar.to_excel(writer, sheet_name='總應收帳款', index=False)
            df_unpaid_ar.to_excel(writer, sheet_name='總未收帳款', index=False)
            df_unpaid_payable.to_excel(writer, sheet_name='未出帳款', index=False)
            df_paid_payable.to_excel(writer, sheet_name='已出帳款', index=False)
        
        return output.getvalue()
    
    except Exception as e:
        st.error(f"❌ 匯出失敗：{e}")
        return None

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
col_date_from, col_date_to, col_type, col_per_page = st.columns([1, 1, 1, 1])

with col_date_from:
    from_date = st.date_input(
        "起始日期",
        value=date(date.today().year, date.today().month, 1),
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

with col_per_page:
    items_per_page = st.selectbox(
        "每頁顯示",
        options=[10, 20, 50, 100],
        index=2,  # 預設選擇 50
        key="items_per_page"
    )

# 查詢按鈕和匯出按鈕
col_query, col_export = st.columns([1, 1])

with col_query:
    apply_date_filter = st.button("🔍 查詢", use_container_width=True, type="primary", key="apply_date_filter")

with col_export:
    st.write("")  # 空行對齊
    st.write("")  # 空行對齊
    # 匯出 Excel 按鈕（使用當前的日期範圍，如果沒有套用日期篩選則匯出全部）
    export_from_date = from_date if apply_date_filter else date(1900, 1, 1)
    export_to_date = to_date if apply_date_filter else date(2100, 12, 31)
    excel_data = export_to_excel(export_from_date, export_to_date)
    
    if excel_data:
        export_filename = f"帳款資料_{datetime.now().strftime('%Y%m%d')}.xlsx"
        st.download_button(
            label="📥 匯出 Excel",
            data=excel_data,
            file_name=export_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_excel"
        )

st.divider()

# ============================================
# 載入帳款資料
# ============================================
try:
    # 初始化分頁狀態
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1
    
    # 如果點擊查詢按鈕、改變帳款類型或改變每頁筆數，重置到第一頁
    if ('prev_items_per_page' not in st.session_state or 
        st.session_state.get('prev_items_per_page') != items_per_page):
        st.session_state['current_page'] = 1
        st.session_state['prev_items_per_page'] = items_per_page
    
    if apply_date_filter or 'prev_ar_type' not in st.session_state or st.session_state.get('prev_ar_type') != ar_type:
        st.session_state['current_page'] = 1
        st.session_state['prev_ar_type'] = ar_type
    
    # 根據選擇的帳款類型查詢不同的資料
    if ar_type == "未出帳款":
        # 查詢未出帳款（應付帳款 - 未付款）
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃合約的未出帳款（業務）
                if apply_date_filter:
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
                else:
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
                        WHERE sales_payment_status != '已付款'
                          AND sales_amount > 0
                    """)
                leasing_sales_data = cur.fetchall()
                
                # 查詢租賃合約的未出帳款（維護）
                if apply_date_filter:
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
                else:
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
                        WHERE service_payment_status != '已付款'
                          AND service_amount > 0
                    """)
                leasing_service_data = cur.fetchall()
                
                # 查詢買斷合約的未出帳款（業務）
                if apply_date_filter:
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
                else:
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
                        WHERE sales_payment_status != '已付款'
                          AND sales_amount > 0
                    """)
                buyout_sales_data = cur.fetchall()
                
                # 查詢買斷合約的未出帳款（維護）
                if apply_date_filter:
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
                else:
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
                        WHERE service_payment_status != '已付款'
                          AND service_amount > 0
                    """)
                buyout_service_data = cur.fetchall()
        
        # 合併所有未出帳款資料
        all_data = leasing_sales_data + leasing_service_data + buyout_sales_data + buyout_service_data
    
    elif ar_type == "已出帳款":
        # 查詢已出帳款（應付帳款 - 已付款）
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃合約的已出帳款（業務）
                if apply_date_filter:
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
                else:
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
                        WHERE sales_payment_status = '已付款'
                          AND sales_amount > 0
                    """)
                leasing_sales_data = cur.fetchall()
                
                # 查詢租賃合約的已出帳款（維護）
                if apply_date_filter:
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
                else:
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
                        WHERE service_payment_status = '已付款'
                          AND service_amount > 0
                    """)
                leasing_service_data = cur.fetchall()
                
                # 查詢買斷合約的已出帳款（業務）
                if apply_date_filter:
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
                else:
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
                        WHERE sales_payment_status = '已付款'
                          AND sales_amount > 0
                    """)
                buyout_sales_data = cur.fetchall()
                
                # 查詢買斷合約的已出帳款（維護）
                if apply_date_filter:
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
                else:
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
                        WHERE service_payment_status = '已付款'
                          AND service_amount > 0
                    """)
                buyout_service_data = cur.fetchall()
        
        # 合併所有已出帳款資料
        all_data = leasing_sales_data + leasing_service_data + buyout_sales_data + buyout_service_data
    else:
        # 查詢應收帳款
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢租賃應收帳款
                if apply_date_filter:
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
                else:
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
                    """)
                leasing_data = cur.fetchall()
                
                # 查詢買斷應收帳款
                if apply_date_filter:
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
                else:
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
                    """)
                buyout_data = cur.fetchall()
        
        # 合併資料
        all_data = leasing_data + buyout_data
    
    if not all_data:
        if apply_date_filter:
            st.info(f"📝 {from_date.strftime('%Y-%m-%d')} ~ {to_date.strftime('%Y-%m-%d')} 沒有帳款資料")
        else:
            st.info(f"📝 目前沒有 {ar_type} 資料")
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
                if apply_date_filter:
                    st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 未出帳款")
                else:
                    st.subheader(f"📊 未出帳款（全部）")
                st.metric(
                    label="💰 總未出帳款金額",
                    value=f"NT$ {total_payable:,.0f}"
                )
            else:  # 已出帳款
                if apply_date_filter:
                    st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 已出帳款")
                else:
                    st.subheader(f"📊 已出帳款（全部）")
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
                if apply_date_filter:
                    st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 總應收帳款")
                else:
                    st.subheader(f"📊 總應收帳款（全部）")
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
                if apply_date_filter:
                    st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 總未收帳款")
                else:
                    st.subheader(f"📊 總未收帳款（全部）")
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
            # 計算總筆數和總頁數
            total_records = len(df)
            total_pages = (total_records + items_per_page - 1) // items_per_page  # 向上取整
            
            # 確保當前頁數不超過總頁數
            if st.session_state['current_page'] > total_pages:
                st.session_state['current_page'] = total_pages if total_pages > 0 else 1
            
            st.write(f"共 {total_records} 筆帳款資料")
            
            # 分頁控制（在表格上方）
            if total_pages > 1:
                col_page_info, col_page_prev, col_page_num, col_page_next, col_page_space = st.columns([2, 1, 2, 1, 6])
                
                with col_page_info:
                    st.write(f"第 {st.session_state['current_page']} 頁 / 共 {total_pages} 頁")
                
                with col_page_prev:
                    if st.button("◀ 上一頁", use_container_width=True, key="prev_page", disabled=(st.session_state['current_page'] == 1)):
                        st.session_state['current_page'] -= 1
                        st.rerun()
                
                with col_page_num:
                    # 頁碼選擇器
                    page_num = st.number_input(
                        "前往頁碼",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state['current_page'],
                        key="page_input",
                        label_visibility="collapsed"
                    )
                    if page_num != st.session_state['current_page']:
                        st.session_state['current_page'] = page_num
                        st.rerun()
                
                with col_page_next:
                    if st.button("下一頁 ▶", use_container_width=True, key="next_page", disabled=(st.session_state['current_page'] == total_pages)):
                        st.session_state['current_page'] += 1
                        st.rerun()
                
                st.divider()
            
            # 根據當前頁數切片 DataFrame
            start_idx = (st.session_state['current_page'] - 1) * items_per_page
            end_idx = start_idx + items_per_page
            df_paged = df.iloc[start_idx:end_idx].copy()
            
            # 編輯按鈕（表格上方）
            col_edit, col_space = st.columns([1, 9])
            
            with col_edit:
                if ar_type in ["未出帳款", "已出帳款"]:
                    # 未出/已出帳款編輯按鈕
                    if st.button("✏️ 編輯帳款", use_container_width=True, key="edit_payable_btn"):
                        # 檢查是否有選擇資料
                        if 'selected_payable_idx' in st.session_state and st.session_state['selected_payable_idx'] is not None:
                            selected_idx = st.session_state['selected_payable_idx']
                            # 調整索引：分頁後的索引 + 當前頁的起始索引
                            actual_idx = start_idx + selected_idx
                            if actual_idx < len(df):
                                selected_row = df.iloc[actual_idx]
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
            
            # 根據帳款類型顯示不同的表格（使用分頁後的資料）
            if ar_type in ["未出帳款", "已出帳款"]:
                # 未出/已出帳款表格
                display_df = df_paged.copy()
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
                
                # 更新選擇狀態（使用分頁後的索引）
                if selection and selection.selection.rows:
                    selected_idx = selection.selection.rows[0]
                    st.session_state['selected_payable_idx'] = selected_idx
                else:
                    st.session_state['selected_payable_idx'] = None
                
                # 顯示已選擇的資料
                if 'selected_payable_idx' in st.session_state and st.session_state['selected_payable_idx'] is not None:
                    selected_idx = st.session_state['selected_payable_idx']
                    actual_idx = start_idx + selected_idx
                    if actual_idx < len(df):
                        selected_row = df.iloc[actual_idx]
                        st.info(f"✓ 已選擇：{selected_row['contract_code']} - {selected_row['customer_name']} ({selected_row['payable_type']})")
            
            else:
                # 應收帳款表格
                # 計算應收總額和未收金額欄位
                df_paged['total_receivable'] = (df_paged['amount'].fillna(0) + df_paged['fee'].fillna(0))
                df_paged['unpaid'] = df_paged['total_receivable'] - df_paged['received_amount'].fillna(0)
                
                # 準備顯示用的 DataFrame
                display_df = df_paged.copy()
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
                
                # 更新選擇狀態（使用分頁後的索引）
                if selection and selection.selection.rows:
                    selected_idx = selection.selection.rows[0]
                    selected_row = df_paged.iloc[selected_idx]
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
            
            # 分頁控制（在表格下方）
            if total_pages > 1:
                st.divider()
                col_page_info2, col_page_prev2, col_page_num2, col_page_next2, col_page_space2 = st.columns([2, 1, 2, 1, 6])
                
                with col_page_info2:
                    st.write(f"第 {st.session_state['current_page']} 頁 / 共 {total_pages} 頁")
                
                with col_page_prev2:
                    if st.button("◀ 上一頁", use_container_width=True, key="prev_page_bottom", disabled=(st.session_state['current_page'] == 1)):
                        st.session_state['current_page'] -= 1
                        st.rerun()
                
                with col_page_num2:
                    page_num2 = st.number_input(
                        "前往頁碼",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state['current_page'],
                        key="page_input_bottom",
                        label_visibility="collapsed"
                    )
                    if page_num2 != st.session_state['current_page']:
                        st.session_state['current_page'] = page_num2
                        st.rerun()
                
                with col_page_next2:
                    if st.button("下一頁 ▶", use_container_width=True, key="next_page_bottom", disabled=(st.session_state['current_page'] == total_pages)):
                        st.session_state['current_page'] += 1
                        st.rerun()

except Exception as e:
    st.error(f"❌ 載入帳款資料失敗：{e}")

