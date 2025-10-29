import streamlit as st
from db_config import get_connection
import pandas as pd

st.set_page_config(page_title="公司資料查詢", page_icon="🏢", layout="wide")

st.title("🏢 公司資料查詢")

# ============================================
# 新增公司 Dialog
# ============================================
@st.dialog("新增公司", width="large")
def add_company_dialog():
    with st.form("add_company_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company_code = st.text_input("公司代碼 *", key="add_code")
            name = st.text_input("公司名稱 *", key="add_name")
            contact_name = st.text_input("聯絡人", key="add_contact")
            mobile = st.text_input("手機", key="add_mobile")
            phone = st.text_input("電話", key="add_phone")
        
        with col2:
            address = st.text_area("地址", key="add_address")
            email = st.text_input("Email", key="add_email")
            tax_id = st.text_input("統編", key="add_tax_id")
            sales_rep = st.text_input("負責業務", key="add_sales_rep")
        
        # 公司類型選擇（checkbox）
        st.divider()
        col_type1, col_type2 = st.columns(2)
        with col_type1:
            is_sales = st.checkbox("是否為業務公司", key="add_is_sales")
        with col_type2:
            is_service = st.checkbox("是否為維護公司", key="add_is_service")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not company_code or not name:
                st.error("公司代碼和公司名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO companies 
                                (company_code, name, contact_name, mobile, phone, address, 
                                 email, tax_id, sales_rep, is_sales, is_service)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (company_code, name, contact_name, mobile, phone, address,
                                  email, tax_id, sales_rep, is_sales, is_service))
                            conn.commit()
                    st.success("✅ 公司新增成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 編輯公司 Dialog
# ============================================
@st.dialog("編輯公司", width="large")
def edit_company_dialog(company_data):
    with st.form("edit_company_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company_code = st.text_input("公司代碼 *", value=company_data['company_code'], disabled=True)
            name = st.text_input("公司名稱 *", value=company_data['name'])
            contact_name = st.text_input("聯絡人", value=company_data['contact_name'] or "")
            mobile = st.text_input("手機", value=company_data['mobile'] or "")
            phone = st.text_input("電話", value=company_data['phone'] or "")
        
        with col2:
            address = st.text_area("地址", value=company_data['address'] or "")
            email = st.text_input("Email", value=company_data['email'] or "")
            tax_id = st.text_input("統編", value=company_data['tax_id'] or "")
            sales_rep = st.text_input("負責業務", value=company_data['sales_rep'] or "")
        
        # 公司類型選擇（checkbox）
        st.divider()
        col_type1, col_type2 = st.columns(2)
        with col_type1:
            is_sales = st.checkbox("是否為業務公司", value=bool(company_data['is_sales']), key="edit_is_sales")
        with col_type2:
            is_service = st.checkbox("是否為維護公司", value=bool(company_data['is_service']), key="edit_is_service")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("公司名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE companies 
                                SET name = %s, contact_name = %s, mobile = %s, phone = %s,
                                    address = %s, email = %s, tax_id = %s, 
                                    sales_rep = %s, is_sales = %s, is_service = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE company_code = %s
                            """, (name, contact_name, mobile, phone, address, email,
                                  tax_id, sales_rep, is_sales, is_service, company_code))
                            conn.commit()
                    st.success("✅ 公司更新成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 搜尋功能（最上方）
# ============================================
search_term = st.text_input("🔍 搜尋公司（可搜尋任何欄位）", placeholder="輸入公司代碼、名稱、聯絡人、手機等...", label_visibility="collapsed")

st.divider()

# ============================================
# 公司類型篩選
# ============================================
col_filter, col_space = st.columns([3, 7])
with col_filter:
    company_type_filter = st.selectbox(
        "公司類型篩選",
        options=["全部", "業務公司", "維護公司", "兩者皆是", "都不是"],
        key="company_type_filter"
    )

st.divider()

# ============================================
# 載入並顯示公司資料
# ============================================
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查詢所有公司資料，按公司代碼排序
            cur.execute("""
                SELECT id, company_code, name, contact_name, mobile, phone, 
                       address, email, tax_id, sales_rep, is_sales, is_service
                FROM companies
                ORDER BY company_code
            """)
            companies = cur.fetchall()
    
    if not companies:
        st.info("📝 目前沒有公司資料")
    else:
        # 轉換為 DataFrame
        columns = ['id', 'company_code', 'name', 'contact_name', 'mobile', 'phone', 
                   'address', 'email', 'tax_id', 'sales_rep', 'is_sales', 'is_service']
        df = pd.DataFrame(companies, columns=columns)
        
        # 根據篩選條件過濾資料
        if company_type_filter == "業務公司":
            df = df[df['is_sales'] == True]
        elif company_type_filter == "維護公司":
            df = df[df['is_service'] == True]
        elif company_type_filter == "兩者皆是":
            df = df[(df['is_sales'] == True) & (df['is_service'] == True)]
        elif company_type_filter == "都不是":
            df = df[(df['is_sales'] == False) & (df['is_service'] == False)]
        # "全部" 則不需要過濾
        
        # 搜尋功能
        if search_term:
            mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
            df = df[mask]
        
        if len(df) == 0:
            st.warning(f"🔍 找不到符合條件的公司資料")
        else:
            st.write(f"共 {len(df)} 筆公司資料")
            
            # 三個按鈕在同一行（表格上方）
            col_add, col_edit, col_delete, col_space = st.columns([1, 1, 1, 7])
            
            with col_add:
                if st.button("➕ 新增公司", use_container_width=True, type="primary"):
                    add_company_dialog()
            
            with col_edit:
                if st.button("✏️ 編輯公司", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_company_id' in st.session_state and st.session_state['selected_company_id'] is not None:
                        selected_id = st.session_state['selected_company_id']
                        if selected_id in df['id'].values:
                            selected_row = df[df['id'] == selected_id].iloc[0]
                            edit_company_dialog(selected_row.to_dict())
                        else:
                            st.warning("⚠️ 請先點選要編輯的公司資料")
                    else:
                        st.warning("⚠️ 請先點選要編輯的公司資料")
            
            with col_delete:
                if st.button("🗑️ 刪除公司", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_company_id' in st.session_state and st.session_state['selected_company_id'] is not None:
                        selected_id = st.session_state['selected_company_id']
                        if selected_id in df['id'].values:
                            st.session_state['confirm_delete_selected'] = selected_id
                        else:
                            st.warning("⚠️ 請先點選要刪除的公司資料")
                    else:
                        st.warning("⚠️ 請先點選要刪除的公司資料")
            
            st.divider()
            
            # 準備顯示用的 DataFrame（隱藏 id，重新命名欄位，添加公司類型標籤）
            display_df = df.copy()
            
            # 創建公司類型標籤欄位
            def get_company_type_label(row):
                if row['is_sales'] and row['is_service']:
                    return "業務+維護"
                elif row['is_sales']:
                    return "業務"
                elif row['is_service']:
                    return "維護"
                else:
                    return "-"
            
            display_df['公司類型'] = display_df.apply(get_company_type_label, axis=1)
            
            display_df = display_df.rename(columns={
                'company_code': '公司代碼',
                'name': '公司名稱',
                'contact_name': '聯絡人',
                'mobile': '手機',
                'phone': '電話',
                'address': '地址',
                'email': 'Email',
                'tax_id': '統編',
                'sales_rep': '負責業務'
            })
            
            # 顯示 DataFrame 表格（可選擇、可排序），包含公司類型欄位
            selection = st.dataframe(
                display_df[['公司代碼', '公司名稱', '公司類型', '聯絡人', '手機', '電話', '地址', 'Email', '統編', '負責業務']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="company_table"
            )
            
            # 更新選擇狀態
            if selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_row = df.iloc[selected_idx]
                st.session_state['selected_company_id'] = selected_row['id']
            else:
                st.session_state['selected_company_id'] = None
            
            # 顯示已選擇的資料
            if 'selected_company_id' in st.session_state and st.session_state['selected_company_id'] is not None:
                selected_id = st.session_state['selected_company_id']
                if selected_id in df['id'].values:
                    selected_row = df[df['id'] == selected_id].iloc[0]
                    st.info(f"✓ 已選擇：{selected_row['name']} ({selected_row['company_code']})")
                    
                    # 刪除確認（二次確認）
                    if st.session_state.get('confirm_delete_selected') == selected_id:
                        st.warning(f"⚠️ 確定要刪除公司「{selected_row['name']}」嗎？此操作無法復原！")
                        col_yes, col_no, col_space2 = st.columns([1, 1, 8])
                        
                        with col_yes:
                            if st.button("✅ 確定刪除", use_container_width=True):
                                try:
                                    with get_connection() as conn:
                                        with conn.cursor() as cur:
                                            # 檢查是否有相關合約資料
                                            cur.execute("""
                                                SELECT COUNT(*) FROM contracts_leasing 
                                                WHERE sales_company_code = %s OR service_company_code = %s
                                            """, (selected_row['company_code'], selected_row['company_code']))
                                            leasing_count = cur.fetchone()[0]
                                            
                                            cur.execute("""
                                                SELECT COUNT(*) FROM contracts_buyout 
                                                WHERE sales_company_code = %s OR service_company_code = %s
                                            """, (selected_row['company_code'], selected_row['company_code']))
                                            buyout_count = cur.fetchone()[0]
                                            
                                            cur.execute("""
                                                SELECT COUNT(*) FROM service_expense 
                                                WHERE repair_company_code = %s
                                            """, (selected_row['company_code'],))
                                            service_count = cur.fetchone()[0]
                                            
                                            total_refs = leasing_count + buyout_count + service_count
                                            
                                            if total_refs > 0:
                                                st.error(f"❌ 無法刪除！此公司有 {total_refs} 筆相關合約或服務記錄，請先處理相關資料。")
                                            else:
                                                # 刪除公司
                                                cur.execute("DELETE FROM companies WHERE id = %s", (selected_id,))
                                                conn.commit()
                                                st.success("✅ 刪除成功！")
                                                if 'confirm_delete_selected' in st.session_state:
                                                    del st.session_state['confirm_delete_selected']
                                                if 'selected_company_id' in st.session_state:
                                                    del st.session_state['selected_company_id']
                                                st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 刪除失敗：{e}")
                        
                        with col_no:
                            if st.button("❌ 取消", use_container_width=True):
                                if 'confirm_delete_selected' in st.session_state:
                                    del st.session_state['confirm_delete_selected']
                                st.rerun()

except Exception as e:
    st.error(f"❌ 載入公司資料失敗：{e}")

