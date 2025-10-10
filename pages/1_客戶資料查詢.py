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
# 新增按鈕
# ============================================
col_btn, col_search = st.columns([1, 3])

with col_btn:
    if st.button("➕ 新增客戶", use_container_width=True, type="primary"):
        add_customer_dialog()

# ============================================
# 搜尋功能
# ============================================
with col_search:
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
        # 轉換為 DataFrame 進行搜尋
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
            
            # 顯示每一筆客戶資料
            for idx, row in df.iterrows():
                with st.container(border=True):
                    # 主要資訊顯示
                    col1, col2, col3, col4, col5, col6 = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1])
                    
                    with col1:
                        st.write(f"**客戶代碼**")
                        st.write(row['customer_code'])
                    
                    with col2:
                        st.write(f"**客戶名稱**")
                        st.write(row['name'])
                    
                    with col3:
                        st.write(f"**聯絡人**")
                        st.write(row['contact_name'] if row['contact_name'] else "-")
                    
                    with col4:
                        st.write(f"**手機**")
                        st.write(row['mobile'] if row['mobile'] else "-")
                    
                    with col5:
                        st.write(f"**統編**")
                        st.write(row['tax_id'] if row['tax_id'] else "-")
                    
                    with col6:
                        # 編輯按鈕
                        if st.button("✏️", key=f"edit_{row['id']}", help="編輯"):
                            edit_customer_dialog(row.to_dict())
                        
                        # 刪除按鈕
                        if st.button("🗑️", key=f"delete_{row['id']}", help="刪除"):
                            st.session_state[f"confirm_delete_{row['id']}"] = True
                    
                    # 刪除確認
                    if st.session_state.get(f"confirm_delete_{row['id']}", False):
                        st.warning(f"⚠️ 確定要刪除客戶「{row['name']}」嗎？")
                        col_yes, col_no, col_space = st.columns([1, 1, 8])
                        
                        with col_yes:
                            if st.button("✅ 確定", key=f"confirm_yes_{row['id']}"):
                                try:
                                    with get_connection() as conn:
                                        with conn.cursor() as cur:
                                            cur.execute("DELETE FROM customers WHERE id = %s", (row['id'],))
                                            conn.commit()
                                    st.success("✅ 刪除成功！")
                                    del st.session_state[f"confirm_delete_{row['id']}"]
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 刪除失敗：{e}")
                        
                        with col_no:
                            if st.button("❌ 取消", key=f"confirm_no_{row['id']}"):
                                del st.session_state[f"confirm_delete_{row['id']}"]
                                st.rerun()
                    
                    # 詳細資料展開
                    with st.expander("📋 查看詳細資料"):
                        col_detail1, col_detail2 = st.columns(2)
                        
                        with col_detail1:
                            st.write(f"**電話：** {row['phone'] if row['phone'] else '-'}")
                            st.write(f"**Email：** {row['email'] if row['email'] else '-'}")
                            st.write(f"**負責業務姓名：** {row['sales_rep_name'] if row['sales_rep_name'] else '-'}")
                        
                        with col_detail2:
                            st.write(f"**地址：** {row['address'] if row['address'] else '-'}")
                            st.write(f"**備註：** {row['remark'] if row['remark'] else '-'}")

except Exception as e:
    st.error(f"❌ 載入客戶資料失敗：{e}")

