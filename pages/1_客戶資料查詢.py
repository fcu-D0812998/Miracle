import streamlit as st
from db_config import get_connection
import pandas as pd

st.set_page_config(page_title="客戶資料查詢", page_icon="👥", layout="wide")

st.title("👥 客戶資料查詢")

# ============================================
# 新增客戶 Dialog
# ============================================
@st.dialog("新增客戶", width="large")
def add_customer_dialog():
    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_code = st.text_input("客戶代碼 *", key="add_code")
            name = st.text_input("客戶名稱 *", key="add_name")
            contact_name = st.text_input("聯絡人", key="add_contact")
            mobile = st.text_input("手機", key="add_mobile")
            phone = st.text_input("電話", key="add_phone")
        
        with col2:
            address = st.text_area("地址", key="add_address")
            email = st.text_input("Email", key="add_email")
            tax_id = st.text_input("統編", key="add_tax_id")
            sales_rep_name = st.text_input("負責業務姓名", key="add_sales")
        
        remark = st.text_area("備註", key="add_remark")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not customer_code or not name:
                st.error("客戶代碼和客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO customers 
                                (customer_code, name, contact_name, mobile, phone, address, 
                                 email, tax_id, sales_rep_name, remark)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (customer_code, name, contact_name, mobile, phone, address,
                                  email, tax_id, sales_rep_name, remark))
                            conn.commit()
                    st.success("✅ 客戶新增成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 編輯客戶 Dialog
# ============================================
@st.dialog("編輯客戶", width="large")
def edit_customer_dialog(customer_data):
    with st.form("edit_customer_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_code = st.text_input("客戶代碼 *", value=customer_data['customer_code'], disabled=True)
            name = st.text_input("客戶名稱 *", value=customer_data['name'])
            contact_name = st.text_input("聯絡人", value=customer_data['contact_name'] or "")
            mobile = st.text_input("手機", value=customer_data['mobile'] or "")
            phone = st.text_input("電話", value=customer_data['phone'] or "")
        
        with col2:
            address = st.text_area("地址", value=customer_data['address'] or "")
            email = st.text_input("Email", value=customer_data['email'] or "")
            tax_id = st.text_input("統編", value=customer_data['tax_id'] or "")
            sales_rep_name = st.text_input("負責業務姓名", value=customer_data['sales_rep_name'] or "")
        
        remark = st.text_area("備註", value=customer_data['remark'] or "")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("客戶名稱為必填欄位！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE customers 
                                SET name = %s, contact_name = %s, mobile = %s, phone = %s,
                                    address = %s, email = %s, tax_id = %s, 
                                    sales_rep_name = %s, remark = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE customer_code = %s
                            """, (name, contact_name, mobile, phone, address, email,
                                  tax_id, sales_rep_name, remark, customer_code))
                            conn.commit()
                    st.success("✅ 客戶更新成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 搜尋功能（最上方）
# ============================================
search_term = st.text_input("🔍 搜尋客戶（可搜尋任何欄位）", placeholder="輸入客戶代碼、名稱、聯絡人、手機等...", label_visibility="collapsed")

st.divider()

# ============================================
# 載入並顯示客戶資料
# ============================================
try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查詢所有客戶資料，按客戶代碼排序
            cur.execute("""
                SELECT id, customer_code, name, contact_name, mobile, phone, 
                       address, email, tax_id, sales_rep_name, remark
                FROM customers
                ORDER BY customer_code
            """)
            customers = cur.fetchall()
    
    if not customers:
        st.info("📝 目前沒有客戶資料")
    else:
        # 轉換為 DataFrame
        columns = ['id', 'customer_code', 'name', 'contact_name', 'mobile', 'phone', 
                   'address', 'email', 'tax_id', 'sales_rep_name', 'remark']
        df = pd.DataFrame(customers, columns=columns)
        
        # 搜尋功能
        if search_term:
            mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
            df = df[mask]
        
        if len(df) == 0:
            st.warning(f"🔍 找不到符合 '{search_term}' 的客戶資料")
        else:
            st.write(f"共 {len(df)} 筆客戶資料")
            
            # 三個按鈕在同一行（表格上方）
            col_add, col_edit, col_delete, col_space = st.columns([1, 1, 1, 7])
            
            with col_add:
                if st.button("➕ 新增客戶", use_container_width=True, type="primary"):
                    add_customer_dialog()
            
            with col_edit:
                if st.button("✏️ 編輯客戶", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_customer_id' in st.session_state and st.session_state['selected_customer_id'] is not None:
                        selected_id = st.session_state['selected_customer_id']
                        if selected_id in df['id'].values:
                            selected_row = df[df['id'] == selected_id].iloc[0]
                            edit_customer_dialog(selected_row.to_dict())
                        else:
                            st.warning("⚠️ 請先點選要編輯的客戶資料")
                    else:
                        st.warning("⚠️ 請先點選要編輯的客戶資料")
            
            with col_delete:
                if st.button("🗑️ 刪除客戶", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_customer_id' in st.session_state and st.session_state['selected_customer_id'] is not None:
                        selected_id = st.session_state['selected_customer_id']
                        if selected_id in df['id'].values:
                            st.session_state['confirm_delete_selected'] = selected_id
                        else:
                            st.warning("⚠️ 請先點選要刪除的客戶資料")
                    else:
                        st.warning("⚠️ 請先點選要刪除的客戶資料")
            
            st.divider()
            
            # 準備顯示用的 DataFrame（隱藏 id，重新命名欄位）
            display_df = df.copy()
            display_df = display_df.rename(columns={
                'customer_code': '客戶代碼',
                'name': '客戶名稱',
                'contact_name': '聯絡人',
                'mobile': '手機',
                'phone': '電話',
                'address': '地址',
                'email': 'Email',
                'tax_id': '統編',
                'sales_rep_name': '負責業務姓名',
                'remark': '備註'
            })
            
            # 顯示 DataFrame 表格（可選擇、可排序）
            selection = st.dataframe(
                display_df[['客戶代碼', '客戶名稱', '聯絡人', '手機', '電話', '地址', 'Email', '統編', '負責業務姓名', '備註']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="customer_table"
            )
            
            # 更新選擇狀態
            if selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_row = df.iloc[selected_idx]
                st.session_state['selected_customer_id'] = selected_row['id']
            else:
                st.session_state['selected_customer_id'] = None
            
            # 顯示已選擇的資料
            if 'selected_customer_id' in st.session_state and st.session_state['selected_customer_id'] is not None:
                selected_id = st.session_state['selected_customer_id']
                if selected_id in df['id'].values:
                    selected_row = df[df['id'] == selected_id].iloc[0]
                    st.info(f"✓ 已選擇：{selected_row['name']} ({selected_row['customer_code']})")
                    
                    # 刪除確認
                    if st.session_state.get('confirm_delete_selected') == selected_id:
                        st.warning(f"⚠️ 確定要刪除客戶「{selected_row['name']}」嗎？此操作無法復原！")
                        col_yes, col_no, col_space2 = st.columns([1, 1, 8])
                        
                        with col_yes:
                            if st.button("✅ 確定刪除", use_container_width=True):
                                try:
                                    with get_connection() as conn:
                                        with conn.cursor() as cur:
                                            cur.execute("DELETE FROM customers WHERE id = %s", (selected_id,))
                                            conn.commit()
                                    st.success("✅ 刪除成功！")
                                    if 'confirm_delete_selected' in st.session_state:
                                        del st.session_state['confirm_delete_selected']
                                    if 'selected_customer_id' in st.session_state:
                                        del st.session_state['selected_customer_id']
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 刪除失敗：{e}")
                        
                        with col_no:
                            if st.button("❌ 取消", use_container_width=True):
                                if 'confirm_delete_selected' in st.session_state:
                                    del st.session_state['confirm_delete_selected']
                                st.rerun()

except Exception as e:
    st.error(f"❌ 載入客戶資料失敗：{e}")

