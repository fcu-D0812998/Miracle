import streamlit as st
from db_config import get_connection
import pandas as pd
from datetime import date

st.set_page_config(page_title="合約資料查詢", page_icon="📄", layout="wide")

st.title("📄 合約資料查詢")

# ============================================
# 載入公司資料
# ============================================
def load_companies():
    """載入公司資料並建立映射"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 載入業務公司
                cur.execute("""
                    SELECT company_code, name 
                    FROM companies 
                    WHERE is_sales = TRUE
                    ORDER BY name
                """)
                sales_companies = cur.fetchall()
                
                # 載入維護公司
                cur.execute("""
                    SELECT company_code, name 
                    FROM companies 
                    WHERE is_service = TRUE
                    ORDER BY name
                """)
                service_companies = cur.fetchall()
        
        # 建立映射字典
        sales_name_to_code = {name: code for code, name in sales_companies}
        sales_code_to_name = {code: name for code, name in sales_companies}
        service_name_to_code = {name: code for code, name in service_companies}
        service_code_to_name = {code: name for code, name in service_companies}
        
        # 建立選項列表（包含「不指定」）
        sales_options = ["不指定"] + [name for _, name in sales_companies]
        service_options = ["不指定"] + [name for _, name in service_companies]
        
        return {
            'sales_name_to_code': sales_name_to_code,
            'sales_code_to_name': sales_code_to_name,
            'service_name_to_code': service_name_to_code,
            'service_code_to_name': service_code_to_name,
            'sales_options': sales_options,
            'service_options': service_options
        }
    except Exception as e:
        st.error(f"❌ 載入公司資料失敗：{e}")
        return None

# 載入公司資料
companies_data = load_companies()
if companies_data is None:
    st.stop()

# ============================================
# 載入客戶資料
# ============================================
def load_customers():
    """載入客戶資料並建立映射"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT customer_code, name 
                    FROM customers 
                    ORDER BY name
                """)
                customers = cur.fetchall()
        
        # 建立映射字典
        customer_name_to_code = {name: code for code, name in customers}
        customer_code_to_name = {code: name for code, name in customers}
        
        # 建立選項列表
        customer_options = [name for _, name in customers]
        
        return {
            'name_to_code': customer_name_to_code,
            'code_to_name': customer_code_to_name,
            'options': customer_options
        }
    except Exception as e:
        st.error(f"❌ 載入客戶資料失敗：{e}")
        return None

# 載入客戶資料
customers_data = load_customers()
if customers_data is None:
    st.stop()

# ============================================
# 自動生成應收帳款函數
# ============================================
def generate_leasing_ar(contract_code, customer_code, customer_name, start_date, 
                        monthly_rent, payment_cycle_months, contract_months, conn):
    """
    根據租賃合約自動生成多筆租賃應收帳款
    """
    from dateutil.relativedelta import relativedelta
    
    try:
        with conn.cursor() as cur:
            # 先刪除該合約的舊應收帳款（用於編輯時）
            cur.execute("DELETE FROM ar_leasing WHERE contract_code = %s", (contract_code,))
            
            # 計算需要生成多少筆
            total_periods = contract_months // payment_cycle_months  # 完整期數
            remaining_months = contract_months % payment_cycle_months  # 剩餘月數
            
            current_start = start_date
            
            # 生成完整期數的應收帳款
            for i in range(total_periods):
                # 計算結束日期（起始日 + 繳費週期月數 - 1天）
                current_end = current_start + relativedelta(months=payment_cycle_months, days=-1)
                # 計算該期總租金
                period_rent = monthly_rent * payment_cycle_months
                
                # 插入應收帳款
                cur.execute("""
                    INSERT INTO ar_leasing 
                    (contract_code, customer_code, customer_name, start_date, end_date, 
                     total_rent, fee, received_amount, payment_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (contract_code, customer_code, customer_name, current_start, current_end,
                      period_rent, 0, 0, '未收'))
                
                # 下一期的起始日 = 本期結束日 + 1天
                current_start = current_end + relativedelta(days=1)
            
            # 如果有剩餘月數，生成最後一筆
            if remaining_months > 0:
                current_end = current_start + relativedelta(months=remaining_months, days=-1)
                period_rent = monthly_rent * remaining_months
                
                cur.execute("""
                    INSERT INTO ar_leasing 
                    (contract_code, customer_code, customer_name, start_date, end_date, 
                     total_rent, fee, received_amount, payment_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (contract_code, customer_code, customer_name, current_start, current_end,
                      period_rent, 0, 0, '未收'))
            
            return True
    except Exception as e:
        raise Exception(f"生成租賃應收帳款失敗：{e}")

def generate_buyout_ar(contract_code, customer_code, customer_name, deal_date, 
                       deal_amount, conn):
    """
    根據買斷合約自動生成買斷應收帳款（1筆）
    """
    try:
        with conn.cursor() as cur:
            # 先刪除該合約的舊應收帳款（用於編輯時）
            cur.execute("DELETE FROM ar_buyout WHERE contract_code = %s", (contract_code,))
            
            # 插入買斷應收帳款
            cur.execute("""
                INSERT INTO ar_buyout 
                (contract_code, customer_code, customer_name, deal_date, 
                 total_amount, fee, received_amount, payment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (contract_code, customer_code, customer_name, deal_date,
                  deal_amount, 0, 0, '未收'))
            
            return True
    except Exception as e:
        raise Exception(f"生成買斷應收帳款失敗：{e}")

# ============================================
# 新增租賃合約 Dialog
# ============================================
@st.dialog("新增租賃合約", width="large")
def add_leasing_dialog():
    with st.form("add_leasing_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            contract_code = st.text_input("合約編號 *", key="add_l_code")
            
            # 客戶名稱下拉選單
            customer_name = st.selectbox(
                "客戶名稱 *",
                options=customers_data['options'],
                key="add_l_customer_name"
            )
            
            start_date = st.date_input("合約起始日 *", key="add_l_start_date", value=date.today())
            model = st.text_input("機型", key="add_l_model")
            quantity = st.number_input("台數", min_value=1, value=1, key="add_l_quantity")
            monthly_rent = st.number_input("月租金", min_value=0.0, value=0.0, step=100.0, key="add_l_rent")
        
        # 自動帶入客戶代碼
        customer_code = customers_data['name_to_code'].get(customer_name, "")
        
        with col2:
            payment_cycle_months = st.number_input("繳費週期（月）", min_value=1, value=1, key="add_l_cycle")
            overprint = st.text_input("超印描述", key="add_l_overprint")
            contract_months = st.number_input("合約期數（月）", min_value=0, value=0, key="add_l_months")
            
            # 業務公司下拉選單
            sales_company_name = st.selectbox(
                "業務公司",
                options=companies_data['sales_options'],
                key="add_l_sales_name"
            )
            sales_amount = st.number_input("業務金額", min_value=0.0, value=0.0, step=100.0, key="add_l_sales_amt")
            
            # 維護公司下拉選單
            service_company_name = st.selectbox(
                "維護公司",
                options=companies_data['service_options'],
                key="add_l_service_name"
            )
            service_amount = st.number_input("維護金額", min_value=0.0, value=0.0, step=100.0, key="add_l_service_amt")
        
        # 轉換公司名稱為代碼
        sales_company_code = companies_data['sales_name_to_code'].get(sales_company_name, None)
        service_company_code = companies_data['service_name_to_code'].get(service_company_name, None)
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not contract_code or not customer_name:
                st.error("合約編號和客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            # 插入租賃合約
                            cur.execute("""
                                INSERT INTO contracts_leasing 
                                (contract_code, customer_code, customer_name, start_date, model, 
                                 quantity, monthly_rent, payment_cycle_months, overprint, contract_months,
                                 sales_company_code, sales_amount, service_company_code, service_amount)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (contract_code, customer_code, customer_name, start_date, model,
                                  quantity, monthly_rent, payment_cycle_months, overprint, contract_months,
                                  sales_company_code, sales_amount, service_company_code, service_amount))
                        
                        # 自動生成租賃應收帳款
                        generate_leasing_ar(
                            contract_code, customer_code, customer_name, start_date,
                            monthly_rent, payment_cycle_months, contract_months, conn
                        )
                        
                        conn.commit()
                    st.success("✅ 租賃合約新增成功！已自動生成應收帳款。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 編輯租賃合約 Dialog
# ============================================
@st.dialog("編輯租賃合約", width="large")
def edit_leasing_dialog(contract_data):
    # 根據已存的 company_code 找到對應的 name
    current_sales_name = "不指定"
    if contract_data['sales_company_code']:
        current_sales_name = companies_data['sales_code_to_name'].get(
            contract_data['sales_company_code'], 
            "不指定"
        )
    
    current_service_name = "不指定"
    if contract_data['service_company_code']:
        current_service_name = companies_data['service_code_to_name'].get(
            contract_data['service_company_code'], 
            "不指定"
        )
    
    # 找到預設值的索引
    sales_index = companies_data['sales_options'].index(current_sales_name) if current_sales_name in companies_data['sales_options'] else 0
    service_index = companies_data['service_options'].index(current_service_name) if current_service_name in companies_data['service_options'] else 0
    
    # 找到客戶名稱的索引
    current_customer_name = contract_data['customer_name'] or ""
    customer_index = customers_data['options'].index(current_customer_name) if current_customer_name in customers_data['options'] else 0
    
    with st.form("edit_leasing_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            contract_code = st.text_input("合約編號 *", value=contract_data['contract_code'], disabled=True)
            
            # 客戶名稱下拉選單
            customer_name = st.selectbox(
                "客戶名稱 *",
                options=customers_data['options'],
                index=customer_index,
                key="edit_l_customer_name"
            )
            start_date = st.date_input("合約起始日 *", value=contract_data['start_date'])
            model = st.text_input("機型", value=contract_data['model'] or "")
            quantity = st.number_input("台數", min_value=1, value=int(contract_data['quantity']) if contract_data['quantity'] else 1)
            monthly_rent = st.number_input("月租金", min_value=0.0, value=float(contract_data['monthly_rent']) if contract_data['monthly_rent'] else 0.0, step=100.0)
        
        # 自動帶入客戶代碼
        customer_code = customers_data['name_to_code'].get(customer_name, "")
        
        with col2:
            payment_cycle_months = st.number_input("繳費週期（月）", min_value=1, value=int(contract_data['payment_cycle_months']) if contract_data['payment_cycle_months'] else 1)
            overprint = st.text_input("超印描述", value=contract_data['overprint'] or "")
            contract_months = st.number_input("合約期數（月）", min_value=0, value=int(contract_data['contract_months']) if contract_data['contract_months'] else 0)
            
            # 業務公司下拉選單
            sales_company_name = st.selectbox(
                "業務公司",
                options=companies_data['sales_options'],
                index=sales_index,
                key="edit_l_sales_name"
            )
            sales_amount = st.number_input("業務金額", min_value=0.0, value=float(contract_data['sales_amount']) if contract_data['sales_amount'] else 0.0, step=100.0)
            
            # 維護公司下拉選單
            service_company_name = st.selectbox(
                "維護公司",
                options=companies_data['service_options'],
                index=service_index,
                key="edit_l_service_name"
            )
            service_amount = st.number_input("維護金額", min_value=0.0, value=float(contract_data['service_amount']) if contract_data['service_amount'] else 0.0, step=100.0)
        
        # 轉換公司名稱為代碼
        sales_company_code = companies_data['sales_name_to_code'].get(sales_company_name, None)
        service_company_code = companies_data['service_name_to_code'].get(service_company_name, None)
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not customer_name:
                st.error("客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            # 更新租賃合約
                            cur.execute("""
                                UPDATE contracts_leasing 
                                SET customer_code = %s, customer_name = %s, start_date = %s, model = %s,
                                    quantity = %s, monthly_rent = %s, payment_cycle_months = %s, 
                                    overprint = %s, contract_months = %s, sales_company_code = %s,
                                    sales_amount = %s, service_company_code = %s, service_amount = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE contract_code = %s
                            """, (customer_code, customer_name, start_date, model, quantity, monthly_rent,
                                  payment_cycle_months, overprint, contract_months, sales_company_code,
                                  sales_amount, service_company_code, service_amount, contract_code))
                        
                        # 重新生成租賃應收帳款
                        generate_leasing_ar(
                            contract_code, customer_code, customer_name, start_date,
                            monthly_rent, payment_cycle_months, contract_months, conn
                        )
                        
                        conn.commit()
                    st.success("✅ 租賃合約更新成功！已重新生成應收帳款。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 新增買斷合約 Dialog
# ============================================
@st.dialog("新增買斷合約", width="large")
def add_buyout_dialog():
    with st.form("add_buyout_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            contract_code = st.text_input("合約編號 *", key="add_b_code")
            
            # 客戶名稱下拉選單
            customer_name = st.selectbox(
                "客戶名稱 *",
                options=customers_data['options'],
                key="add_b_customer_name"
            )
            
            deal_date = st.date_input("成交日期 *", key="add_b_deal_date", value=date.today())
            deal_amount = st.number_input("成交金額", min_value=0.0, value=0.0, step=100.0, key="add_b_deal_amt")
        
        # 自動帶入客戶代碼
        customer_code = customers_data['name_to_code'].get(customer_name, "")
        
        with col2:
            # 業務公司下拉選單
            sales_company_name = st.selectbox(
                "業務公司",
                options=companies_data['sales_options'],
                key="add_b_sales_name"
            )
            sales_amount = st.number_input("業務金額", min_value=0.0, value=0.0, step=100.0, key="add_b_sales_amt")
            
            # 維護公司下拉選單
            service_company_name = st.selectbox(
                "維護公司",
                options=companies_data['service_options'],
                key="add_b_service_name"
            )
            service_amount = st.number_input("維護金額", min_value=0.0, value=0.0, step=100.0, key="add_b_service_amt")
        
        # 轉換公司名稱為代碼
        sales_company_code = companies_data['sales_name_to_code'].get(sales_company_name, None)
        service_company_code = companies_data['service_name_to_code'].get(service_company_name, None)
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not contract_code or not customer_name:
                st.error("合約編號和客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            # 插入買斷合約
                            cur.execute("""
                                INSERT INTO contracts_buyout 
                                (contract_code, customer_code, customer_name, deal_date, deal_amount,
                                 sales_company_code, sales_amount, service_company_code, service_amount)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (contract_code, customer_code, customer_name, deal_date, deal_amount,
                                  sales_company_code, sales_amount, service_company_code, service_amount))
                        
                        # 自動生成買斷應收帳款
                        generate_buyout_ar(
                            contract_code, customer_code, customer_name, deal_date,
                            deal_amount, conn
                        )
                        
                        conn.commit()
                    st.success("✅ 買斷合約新增成功！已自動生成應收帳款。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 編輯買斷合約 Dialog
# ============================================
@st.dialog("編輯買斷合約", width="large")
def edit_buyout_dialog(contract_data):
    # 根據已存的 company_code 找到對應的 name
    current_sales_name = "不指定"
    if contract_data['sales_company_code']:
        current_sales_name = companies_data['sales_code_to_name'].get(
            contract_data['sales_company_code'], 
            "不指定"
        )
    
    current_service_name = "不指定"
    if contract_data['service_company_code']:
        current_service_name = companies_data['service_code_to_name'].get(
            contract_data['service_company_code'], 
            "不指定"
        )
    
    # 找到預設值的索引
    sales_index = companies_data['sales_options'].index(current_sales_name) if current_sales_name in companies_data['sales_options'] else 0
    service_index = companies_data['service_options'].index(current_service_name) if current_service_name in companies_data['service_options'] else 0
    
    # 找到客戶名稱的索引
    current_customer_name = contract_data['customer_name'] or ""
    customer_index = customers_data['options'].index(current_customer_name) if current_customer_name in customers_data['options'] else 0
    
    with st.form("edit_buyout_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            contract_code = st.text_input("合約編號 *", value=contract_data['contract_code'], disabled=True)
            
            # 客戶名稱下拉選單
            customer_name = st.selectbox(
                "客戶名稱 *",
                options=customers_data['options'],
                index=customer_index,
                key="edit_b_customer_name"
            )
            
            deal_date = st.date_input("成交日期 *", value=contract_data['deal_date'])
            deal_amount = st.number_input("成交金額", min_value=0.0, value=float(contract_data['deal_amount']) if contract_data['deal_amount'] else 0.0, step=100.0)
        
        # 自動帶入客戶代碼
        customer_code = customers_data['name_to_code'].get(customer_name, "")
        
        with col2:
            # 業務公司下拉選單
            sales_company_name = st.selectbox(
                "業務公司",
                options=companies_data['sales_options'],
                index=sales_index,
                key="edit_b_sales_name"
            )
            sales_amount = st.number_input("業務金額", min_value=0.0, value=float(contract_data['sales_amount']) if contract_data['sales_amount'] else 0.0, step=100.0)
            
            # 維護公司下拉選單
            service_company_name = st.selectbox(
                "維護公司",
                options=companies_data['service_options'],
                index=service_index,
                key="edit_b_service_name"
            )
            service_amount = st.number_input("維護金額", min_value=0.0, value=float(contract_data['service_amount']) if contract_data['service_amount'] else 0.0, step=100.0)
        
        # 轉換公司名稱為代碼
        sales_company_code = companies_data['sales_name_to_code'].get(sales_company_name, None)
        service_company_code = companies_data['service_name_to_code'].get(service_company_name, None)
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not customer_name:
                st.error("客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            # 更新買斷合約
                            cur.execute("""
                                UPDATE contracts_buyout 
                                SET customer_code = %s, customer_name = %s, deal_date = %s, deal_amount = %s,
                                    sales_company_code = %s, sales_amount = %s, 
                                    service_company_code = %s, service_amount = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE contract_code = %s
                            """, (customer_code, customer_name, deal_date, deal_amount,
                                  sales_company_code, sales_amount, service_company_code, 
                                  service_amount, contract_code))
                        
                        # 重新生成買斷應收帳款
                        generate_buyout_ar(
                            contract_code, customer_code, customer_name, deal_date,
                            deal_amount, conn
                        )
                        
                        conn.commit()
                    st.success("✅ 買斷合約更新成功！已重新生成應收帳款。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 選擇合約類型
# ============================================
col_type, col_btn, col_search = st.columns([1, 1, 2])

with col_type:
    contract_type = st.selectbox(
        "合約類型",
        options=["租賃合約", "買斷合約"],
        key="contract_type_select"
    )

with col_btn:
    if contract_type == "租賃合約":
        if st.button("➕ 新增租賃合約", use_container_width=True, type="primary"):
            add_leasing_dialog()
    else:
        if st.button("➕ 新增買斷合約", use_container_width=True, type="primary"):
            add_buyout_dialog()

# ============================================
# 搜尋功能
# ============================================
with col_search:
    search_term = st.text_input("🔍 搜尋合約（可搜尋任何欄位）", placeholder="輸入合約編號、客戶名稱等...", label_visibility="collapsed")

st.divider()

# ============================================
# 顯示租賃合約
# ============================================
if contract_type == "租賃合約":
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, contract_code, customer_code, customer_name, start_date, 
                           model, quantity, monthly_rent, payment_cycle_months, overprint, 
                           contract_months, sales_company_code, sales_amount, 
                           service_company_code, service_amount
                    FROM contracts_leasing
                    ORDER BY contract_code
                """)
                contracts = cur.fetchall()
        
        if not contracts:
            st.info("📝 目前沒有租賃合約資料")
        else:
            # 轉換為 DataFrame
            columns = ['id', 'contract_code', 'customer_code', 'customer_name', 'start_date',
                      'model', 'quantity', 'monthly_rent', 'payment_cycle_months', 'overprint',
                      'contract_months', 'sales_company_code', 'sales_amount',
                      'service_company_code', 'service_amount']
            df = pd.DataFrame(contracts, columns=columns)
            
            # 搜尋功能
            if search_term:
                mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
                df = df[mask]
            
            if len(df) == 0:
                st.warning(f"🔍 找不到符合 '{search_term}' 的租賃合約")
            else:
                st.write(f"共 {len(df)} 筆租賃合約")
                
                # 顯示每一筆合約
                for idx, row in df.iterrows():
                    with st.container(border=True):
                        # 主要資訊顯示
                        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 1.5, 1, 1.5, 0.8, 1, 1, 0.8])
                        
                        with col1:
                            st.write(f"**合約編號**")
                            st.write(row['contract_code'])
                        
                        with col2:
                            st.write(f"**客戶名稱**")
                            st.write(row['customer_name'])
                        
                        with col3:
                            st.write(f"**起始日**")
                            st.write(row['start_date'].strftime('%Y-%m-%d') if row['start_date'] else "-")
                        
                        with col4:
                            st.write(f"**機型**")
                            st.write(row['model'] if row['model'] else "-")
                        
                        with col5:
                            st.write(f"**台數**")
                            st.write(f"{row['quantity']} 台" if row['quantity'] else "-")
                        
                        with col6:
                            st.write(f"**月租金**")
                            st.write(f"NT$ {row['monthly_rent']:,.0f}" if row['monthly_rent'] else "-")
                        
                        with col7:
                            st.write(f"**合約期數**")
                            st.write(f"{row['contract_months']} 月" if row['contract_months'] else "-")
                        
                        with col8:
                            # 編輯按鈕
                            if st.button("✏️", key=f"edit_l_{row['id']}", help="編輯"):
                                edit_leasing_dialog(row.to_dict())
                            
                            # 刪除按鈕
                            if st.button("🗑️", key=f"delete_l_{row['id']}", help="刪除"):
                                st.session_state[f"confirm_delete_l_{row['id']}"] = True
                        
                        # 刪除確認
                        if st.session_state.get(f"confirm_delete_l_{row['id']}", False):
                            st.warning(f"⚠️ 確定要刪除合約「{row['contract_code']}」嗎？")
                            col_yes, col_no, col_space = st.columns([1, 1, 8])
                            
                            with col_yes:
                                if st.button("✅ 確定", key=f"confirm_yes_l_{row['id']}"):
                                    try:
                                        with get_connection() as conn:
                                            with conn.cursor() as cur:
                                                cur.execute("DELETE FROM contracts_leasing WHERE id = %s", (row['id'],))
                                                conn.commit()
                                        st.success("✅ 刪除成功！")
                                        del st.session_state[f"confirm_delete_l_{row['id']}"]
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 刪除失敗：{e}")
                            
                            with col_no:
                                if st.button("❌ 取消", key=f"confirm_no_l_{row['id']}"):
                                    del st.session_state[f"confirm_delete_l_{row['id']}"]
                                    st.rerun()
                        
                        # 詳細資料展開
                        with st.expander("📋 查看詳細資料"):
                            col_detail1, col_detail2 = st.columns(2)
                            
                            with col_detail1:
                                st.write(f"**客戶代碼：** {row['customer_code'] if row['customer_code'] else '-'}")
                                st.write(f"**繳費週期：** {row['payment_cycle_months']} 個月" if row['payment_cycle_months'] else "**繳費週期：** -")
                                st.write(f"**超印描述：** {row['overprint'] if row['overprint'] else '-'}")
                                st.write(f"**業務公司代碼：** {row['sales_company_code'] if row['sales_company_code'] else '-'}")
                                st.write(f"**業務金額：** NT$ {row['sales_amount']:,.0f}" if row['sales_amount'] else "**業務金額：** -")
                            
                            with col_detail2:
                                st.write(f"**維護公司代碼：** {row['service_company_code'] if row['service_company_code'] else '-'}")
                                st.write(f"**維護金額：** NT$ {row['service_amount']:,.0f}" if row['service_amount'] else "**維護金額：** -")
    
    except Exception as e:
        st.error(f"❌ 載入租賃合約資料失敗：{e}")

# ============================================
# 顯示買斷合約
# ============================================
else:  # 買斷合約
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, contract_code, customer_code, customer_name, deal_date, 
                           deal_amount, sales_company_code, sales_amount, 
                           service_company_code, service_amount
                    FROM contracts_buyout
                    ORDER BY contract_code
                """)
                contracts = cur.fetchall()
        
        if not contracts:
            st.info("📝 目前沒有買斷合約資料")
        else:
            # 轉換為 DataFrame
            columns = ['id', 'contract_code', 'customer_code', 'customer_name', 'deal_date',
                      'deal_amount', 'sales_company_code', 'sales_amount',
                      'service_company_code', 'service_amount']
            df = pd.DataFrame(contracts, columns=columns)
            
            # 搜尋功能
            if search_term:
                mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
                df = df[mask]
            
            if len(df) == 0:
                st.warning(f"🔍 找不到符合 '{search_term}' 的買斷合約")
            else:
                st.write(f"共 {len(df)} 筆買斷合約")
                
                # 顯示每一筆合約
                for idx, row in df.iterrows():
                    with st.container(border=True):
                        # 主要資訊顯示
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 0.8])
                        
                        with col1:
                            st.write(f"**合約編號**")
                            st.write(row['contract_code'])
                        
                        with col2:
                            st.write(f"**客戶名稱**")
                            st.write(row['customer_name'])
                        
                        with col3:
                            st.write(f"**成交日期**")
                            st.write(row['deal_date'].strftime('%Y-%m-%d') if row['deal_date'] else "-")
                        
                        with col4:
                            st.write(f"**成交金額**")
                            st.write(f"NT$ {row['deal_amount']:,.0f}" if row['deal_amount'] else "-")
                        
                        with col5:
                            # 編輯按鈕
                            if st.button("✏️", key=f"edit_b_{row['id']}", help="編輯"):
                                edit_buyout_dialog(row.to_dict())
                            
                            # 刪除按鈕
                            if st.button("🗑️", key=f"delete_b_{row['id']}", help="刪除"):
                                st.session_state[f"confirm_delete_b_{row['id']}"] = True
                        
                        # 刪除確認
                        if st.session_state.get(f"confirm_delete_b_{row['id']}", False):
                            st.warning(f"⚠️ 確定要刪除合約「{row['contract_code']}」嗎？")
                            col_yes, col_no, col_space = st.columns([1, 1, 8])
                            
                            with col_yes:
                                if st.button("✅ 確定", key=f"confirm_yes_b_{row['id']}"):
                                    try:
                                        with get_connection() as conn:
                                            with conn.cursor() as cur:
                                                cur.execute("DELETE FROM contracts_buyout WHERE id = %s", (row['id'],))
                                                conn.commit()
                                        st.success("✅ 刪除成功！")
                                        del st.session_state[f"confirm_delete_b_{row['id']}"]
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 刪除失敗：{e}")
                            
                            with col_no:
                                if st.button("❌ 取消", key=f"confirm_no_b_{row['id']}"):
                                    del st.session_state[f"confirm_delete_b_{row['id']}"]
                                    st.rerun()
                        
                        # 詳細資料展開
                        with st.expander("📋 查看詳細資料"):
                            col_detail1, col_detail2 = st.columns(2)
                            
                            with col_detail1:
                                st.write(f"**客戶代碼：** {row['customer_code'] if row['customer_code'] else '-'}")
                                st.write(f"**業務公司代碼：** {row['sales_company_code'] if row['sales_company_code'] else '-'}")
                                st.write(f"**業務金額：** NT$ {row['sales_amount']:,.0f}" if row['sales_amount'] else "**業務金額：** -")
                            
                            with col_detail2:
                                st.write(f"**維護公司代碼：** {row['service_company_code'] if row['service_company_code'] else '-'}")
                                st.write(f"**維護金額：** NT$ {row['service_amount']:,.0f}" if row['service_amount'] else "**維護金額：** -")
    
    except Exception as e:
        st.error(f"❌ 載入買斷合約資料失敗：{e}")

