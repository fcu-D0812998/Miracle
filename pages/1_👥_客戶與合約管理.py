import streamlit as st
import pandas as pd
from db_config import get_connection

# 設定頁面
st.set_page_config(page_title="客戶與合約管理", page_icon="👥", layout="wide")

# 檢查登入狀態
if "user" not in st.session_state:
    st.error("❌ 請先登入")
    st.stop()

st.title("👥 客戶與合約管理")

# ============================================
# 上半部：客戶資料管理
# ============================================
st.subheader("📋 客戶列表")

# 搜尋功能
search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    search_keyword = st.text_input("🔍 搜尋客戶", placeholder="輸入客戶代碼或公司名稱...")
with search_col2:
    if st.button("➕ 新增客戶", use_container_width=True, type="primary"):
        st.session_state["adding_customer"] = True

# 載入客戶列表
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if search_keyword:
                cur.execute("""
                    SELECT 
                        c.id, c.code, c.name, c.contact, c.phone, 
                        c.email, c.address, c.tax_id, 
                        comp.name AS sales_company, c.note, c.status
                    FROM customers c
                    LEFT JOIN companies comp ON c.sales_company_id = comp.id
                    WHERE c.status = 'ACTIVE' 
                      AND (c.code ILIKE %s OR c.name ILIKE %s)
                    ORDER BY c.id DESC
                """, (f"%{search_keyword}%", f"%{search_keyword}%"))
            else:
                cur.execute("""
                    SELECT 
                        c.id, c.code, c.name, c.contact, c.phone, 
                        c.email, c.address, c.tax_id, 
                        comp.name AS sales_company, c.note, c.status
                    FROM customers c
                    LEFT JOIN companies comp ON c.sales_company_id = comp.id
                    WHERE c.status = 'ACTIVE'
                    ORDER BY c.id DESC
                """)
            customers = cur.fetchall()

    if customers:
        for customer in customers:
            cust_id, code, name, contact, phone, email, address, tax_id, sales_company, note, status = customer
            
            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])
                
                with col1:
                    st.markdown(f"### {code} - {name}")
                    info_col1, info_col2, info_col3 = st.columns(3)
                    with info_col1:
                        st.write(f"**聯絡人：** {contact or '-'}")
                        st.write(f"**電話：** {phone or '-'}")
                    with info_col2:
                        st.write(f"**信箱：** {email or '-'}")
                        st.write(f"**統編：** {tax_id or '-'}")
                    with info_col3:
                        st.write(f"**負責業務：** {sales_company or '-'}")
                        st.write(f"**地址：** {address or '-'}")
                
                with col2:
                    if st.button("📝 編輯", key=f"edit_cust_{cust_id}", use_container_width=True):
                        st.session_state["editing_customer"] = cust_id
                        st.session_state["selected_customer"] = cust_id
                
                with col3:
                    if st.button("📄 合約", key=f"view_contracts_{cust_id}", use_container_width=True, type="primary"):
                        st.session_state["selected_customer"] = cust_id
                
                st.divider()
    else:
        st.info("目前無客戶資料" + ("符合搜尋條件" if search_keyword else ""))

except Exception as e:
    st.error(f"❌ 載入客戶列表失敗：{e}")

# ============================================
# 新增客戶表單
# ============================================
if st.session_state.get("adding_customer", False):
    st.markdown("---")
    st.subheader("➕ 新增客戶")
    
    # 載入業務公司列表
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM companies WHERE is_sales = TRUE ORDER BY name")
                sales_companies = cur.fetchall()
    except Exception as e:
        st.error(f"❌ 載入業務公司失敗：{e}")
        sales_companies = []
    
    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_code = st.text_input("客戶代碼 *", placeholder="例：C001")
            new_name = st.text_input("公司名稱 *", placeholder="例：ABC 印刷公司")
            new_contact = st.text_input("聯絡人姓名", placeholder="例：張三")
            new_phone = st.text_input("電話（手機/市話）", placeholder="例：0912-345678 或 02-12345678")
            new_email = st.text_input("信箱", placeholder="例：contact@abc.com")
        
        with col2:
            new_address = st.text_input("地址", placeholder="例：台北市中正區...")
            new_tax_id = st.text_input("統編", placeholder="例：12345678")
            
            # 業務公司選擇
            sales_col1, sales_col2 = st.columns([4, 1])
            with sales_col1:
                sales_options = {comp[1]: comp[0] for comp in sales_companies}
                sales_options["（無）"] = None
                selected_sales = st.selectbox("負責業務", list(sales_options.keys()))
            with sales_col2:
                if st.form_submit_button("➕", help="新增業務公司"):
                    st.session_state["adding_sales_company"] = True
            
            new_note = st.text_area("備註", placeholder="其他說明...")
        
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            if st.form_submit_button("✅ 新增客戶", type="primary", use_container_width=True):
                if not new_code or not new_name:
                    st.error("❌ 請至少輸入客戶代碼與公司名稱")
                else:
                    try:
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    INSERT INTO customers (
                                        code, name, contact, phone, email, 
                                        address, tax_id, sales_company_id, note, status
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                                """, (new_code, new_name, new_contact, new_phone, new_email,
                                      new_address, new_tax_id, sales_options[selected_sales], new_note))
                            conn.commit()
                        
                        st.success(f"✅ 客戶 {new_name} 新增成功！")
                        st.session_state["adding_customer"] = False
                        st.rerun()
                    
                    except Exception as e:
                        if "unique constraint" in str(e).lower():
                            st.error(f"❌ 客戶代碼 '{new_code}' 已存在")
                        else:
                            st.error(f"❌ 新增失敗：{e}")
        
        with submit_col2:
            if st.form_submit_button("❌ 取消", use_container_width=True):
                st.session_state["adding_customer"] = False
                st.rerun()

# ============================================
# 編輯客戶表單
# ============================================
if "editing_customer" in st.session_state:
    st.markdown("---")
    st.subheader("📝 編輯客戶")
    
    cust_id = st.session_state["editing_customer"]
    
    # 載入客戶資料
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT code, name, contact, phone, email, address, 
                           tax_id, sales_company_id, note
                    FROM customers WHERE id = %s
                """, (cust_id,))
                cust_data = cur.fetchone()
                
                cur.execute("SELECT id, name FROM companies WHERE is_sales = TRUE ORDER BY name")
                sales_companies = cur.fetchall()
        
        if cust_data:
            code, name, contact, phone, email, address, tax_id, sales_company_id, note = cust_data
            
            with st.form("edit_customer_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    edit_code = st.text_input("客戶代碼 *", value=code)
                    edit_name = st.text_input("公司名稱 *", value=name)
                    edit_contact = st.text_input("聯絡人姓名", value=contact or "")
                    edit_phone = st.text_input("電話", value=phone or "")
                    edit_email = st.text_input("信箱", value=email or "")
                
                with col2:
                    edit_address = st.text_input("地址", value=address or "")
                    edit_tax_id = st.text_input("統編", value=tax_id or "")
                    
                    sales_options = {comp[1]: comp[0] for comp in sales_companies}
                    sales_options["（無）"] = None
                    current_sales = next((name for name, id in sales_options.items() if id == sales_company_id), "（無）")
                    edit_sales = st.selectbox("負責業務", list(sales_options.keys()), index=list(sales_options.keys()).index(current_sales))
                    
                    edit_note = st.text_area("備註", value=note or "")
                
                submit_col1, submit_col2 = st.columns(2)
                with submit_col1:
                    if st.form_submit_button("✅ 儲存", type="primary", use_container_width=True):
                        try:
                            with get_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("""
                                        UPDATE customers 
                                        SET code = %s, name = %s, contact = %s, phone = %s, 
                                            email = %s, address = %s, tax_id = %s, 
                                            sales_company_id = %s, note = %s
                                        WHERE id = %s
                                    """, (edit_code, edit_name, edit_contact, edit_phone, edit_email,
                                          edit_address, edit_tax_id, sales_options[edit_sales], edit_note, cust_id))
                                conn.commit()
                            
                            st.success("✅ 客戶資料已更新")
                            del st.session_state["editing_customer"]
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ 更新失敗：{e}")
                
                with submit_col2:
                    if st.form_submit_button("❌ 取消", use_container_width=True):
                        del st.session_state["editing_customer"]
                        st.rerun()
    
    except Exception as e:
        st.error(f"❌ 載入客戶資料失敗：{e}")

# ============================================
# 下半部：選中客戶的合約列表
# ============================================
if "selected_customer" in st.session_state:
    st.markdown("---")
    st.markdown("---")
    
    selected_cust_id = st.session_state["selected_customer"]
    
    # 載入客戶名稱
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT code, name FROM customers WHERE id = %s", (selected_cust_id,))
                cust_info = cur.fetchone()
        
        if cust_info:
            cust_code, cust_name = cust_info
            st.subheader(f"📄 {cust_code} - {cust_name} 的合約列表")
            
            # 新增合約按鈕
            if st.button("➕ 新增合約", type="primary"):
                st.session_state["adding_contract"] = selected_cust_id
            
            # 載入合約列表
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            c.id, c.kind, c.start_date, c.end_date, c.model,
                            c.pay_mode_months, c.term_months,
                            c.bw_included, c.color_included, c.bw_rate, c.color_rate,
                            sales.name AS sales_company, c.sales_commission,
                            maint.name AS maint_company, c.maint_commission,
                            c.status
                        FROM contracts c
                        LEFT JOIN companies sales ON c.sales_company_id = sales.id
                        LEFT JOIN companies maint ON c.maint_company_id = maint.id
                        WHERE c.customer_id = %s
                        ORDER BY c.start_date DESC
                    """, (selected_cust_id,))
                    contracts = cur.fetchall()
            
            if contracts:
                for contract in contracts:
                    (contract_id, kind, start_date, end_date, model, pay_mode, term_months,
                     bw_inc, color_inc, bw_rate, color_rate, sales_comp, sales_comm,
                     maint_comp, maint_comm, status) = contract
                    
                    with st.expander(f"合約 #{contract_id} - {kind} - {model or '未設定機型'} ({status})"):
                        info_col1, info_col2, info_col3 = st.columns(3)
                        
                        with info_col1:
                            st.write(f"**類型：** {kind}")
                            st.write(f"**機型：** {model or '-'}")
                            st.write(f"**起始日：** {start_date}")
                            st.write(f"**結束日：** {end_date or '未設定'}")
                        
                        with info_col2:
                            st.write(f"**繳費模式：** {pay_mode} 月")
                            st.write(f"**合約期數：** {term_months or '-'} 月")
                            st.write(f"**黑白含量：** {bw_inc} 張")
                            st.write(f"**彩色含量：** {color_inc} 張")
                        
                        with info_col3:
                            st.write(f"**黑白超印：** NT$ {bw_rate}/張")
                            st.write(f"**彩色超印：** NT$ {color_rate}/張")
                            st.write(f"**業務：** {sales_comp or '-'} (NT$ {sales_comm or 0})")
                            st.write(f"**維護：** {maint_comp or '-'} (NT$ {maint_comm or 0})")
                        
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("📝 編輯合約", key=f"edit_contract_{contract_id}"):
                                st.session_state["editing_contract"] = contract_id
                        with btn_col2:
                            if st.button("🗑️ 停用合約", key=f"close_contract_{contract_id}"):
                                st.session_state["closing_contract"] = contract_id
            else:
                st.info("此客戶尚無合約")
    
    except Exception as e:
        st.error(f"❌ 載入合約列表失敗：{e}")

# ============================================
# 新增合約表單
# ============================================
if "adding_contract" in st.session_state:
    st.markdown("---")
    st.subheader("➕ 新增合約")
    
    customer_id = st.session_state["adding_contract"]
    
    # 載入公司列表
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM companies WHERE is_sales = TRUE ORDER BY name")
                sales_companies = cur.fetchall()
                cur.execute("SELECT id, name FROM companies WHERE is_maintenance = TRUE ORDER BY name")
                maint_companies = cur.fetchall()
    except Exception as e:
        st.error(f"❌ 載入公司列表失敗：{e}")
        sales_companies = []
        maint_companies = []
    
    with st.form("add_contract_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            contract_kind = st.radio("合約類型 *", ["RENT", "BUYOUT"], horizontal=True, format_func=lambda x: "租賃" if x == "RENT" else "買斷")
            contract_model = st.text_input("機型 *", placeholder="例：HP LaserJet Pro M404dn")
            contract_start = st.date_input("合約起始日 *")
            contract_end = st.date_input("合約結束日（選填）", value=None)
            contract_term = st.number_input("合約期數（月）", min_value=1, max_value=120, value=12)
        
        with col2:
            contract_pay_mode = st.number_input("繳費模式（月）", min_value=1, max_value=12, value=1, help="1=月繳, 3=季繳, 6=半年, 12=年")
            contract_bw_inc = st.number_input("黑白含量（張）", min_value=0, value=0)
            contract_color_inc = st.number_input("彩色含量（張）", min_value=0, value=0)
            contract_bw_rate = st.number_input("黑白超印單價（元/張）", min_value=0.0, value=0.0, step=0.1)
            contract_color_rate = st.number_input("彩色超印單價（元/張）", min_value=0.0, value=0.0, step=0.1)
        
        with col3:
            # 業務公司與佣金
            st.markdown("**業務公司與佣金**")
            sales_col1, sales_col2 = st.columns([3, 1])
            with sales_col1:
                sales_options = {comp[1]: comp[0] for comp in sales_companies}
                sales_options["（無）"] = None
                selected_sales_comp = st.selectbox("業務公司", list(sales_options.keys()), key="new_sales_comp")
            with sales_col2:
                if st.form_submit_button("➕ 業務", help="新增業務公司"):
                    st.session_state["adding_sales_company_in_contract"] = True
            
            contract_sales_comm = st.number_input("業務佣金（元）", min_value=0.0, value=0.0, step=100.0)
            
            # 維護公司與佣金
            st.markdown("**維護公司與佣金**")
            maint_col1, maint_col2 = st.columns([3, 1])
            with maint_col1:
                maint_options = {comp[1]: comp[0] for comp in maint_companies}
                maint_options["（無）"] = None
                selected_maint_comp = st.selectbox("維護公司", list(maint_options.keys()), key="new_maint_comp")
            with maint_col2:
                if st.form_submit_button("➕ 維護", help="新增維護公司"):
                    st.session_state["adding_maint_company_in_contract"] = True
            
            contract_maint_comm = st.number_input("維護佣金（元）", min_value=0.0, value=0.0, step=100.0)
        
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            if st.form_submit_button("✅ 新增合約", type="primary", use_container_width=True):
                if not contract_model:
                    st.error("❌ 請輸入機型")
                else:
                    try:
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    INSERT INTO contracts (
                                        customer_id, kind, start_date, end_date, model,
                                        pay_mode_months, term_months,
                                        bw_included, color_included, bw_rate, color_rate,
                                        sales_company_id, sales_commission,
                                        maint_company_id, maint_commission,
                                        status
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                                """, (customer_id, contract_kind, contract_start, contract_end, contract_model,
                                      contract_pay_mode, contract_term,
                                      contract_bw_inc, contract_color_inc, contract_bw_rate, contract_color_rate,
                                      sales_options[selected_sales_comp], contract_sales_comm,
                                      maint_options[selected_maint_comp], contract_maint_comm))
                            conn.commit()
                        
                        st.success(f"✅ 合約新增成功！")
                        del st.session_state["adding_contract"]
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ 新增失敗：{e}")
        
        with submit_col2:
            if st.form_submit_button("❌ 取消", use_container_width=True):
                del st.session_state["adding_contract"]
                st.rerun()

# ============================================
# 新增公司快速表單（彈出式）
# ============================================
if st.session_state.get("adding_sales_company_in_contract", False) or st.session_state.get("adding_maint_company_in_contract", False):
    st.markdown("---")
    
    company_type = "sales" if st.session_state.get("adding_sales_company_in_contract", False) else "maintenance"
    st.subheader(f"➕ 新增{'業務' if company_type == 'sales' else '維護'}公司")
    
    with st.form("add_company_quick_form"):
        new_company_name = st.text_input("公司名稱 *", placeholder="例：ABC 業務公司")
        
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            if st.form_submit_button("✅ 新增", type="primary", use_container_width=True):
                if not new_company_name:
                    st.error("❌ 請輸入公司名稱")
                else:
                    try:
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    INSERT INTO companies (name, is_sales, is_maintenance)
                                    VALUES (%s, %s, %s)
                                """, (new_company_name, 
                                      company_type == "sales", 
                                      company_type == "maintenance"))
                            conn.commit()
                        
                        st.success(f"✅ 公司 {new_company_name} 新增成功！")
                        if company_type == "sales":
                            del st.session_state["adding_sales_company_in_contract"]
                        else:
                            del st.session_state["adding_maint_company_in_contract"]
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ 新增失敗：{e}")
        
        with submit_col2:
            if st.form_submit_button("❌ 取消", use_container_width=True):
                if company_type == "sales":
                    del st.session_state["adding_sales_company_in_contract"]
                else:
                    del st.session_state["adding_maint_company_in_contract"]
                st.rerun()
