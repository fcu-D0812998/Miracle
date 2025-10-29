import streamlit as st
from db_config import get_connection
import pandas as pd
from datetime import date, datetime
from io import BytesIO

st.set_page_config(page_title="銀行帳本查詢", page_icon="🏦", layout="wide")

st.title("🏦 銀行帳本查詢")

# ============================================
# 匯出 Excel 功能
# ============================================
def export_to_excel(from_date, to_date):
    """匯出銀行帳本資料到 Excel"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if from_date and to_date:
                    cur.execute("""
                        SELECT txn_date, payer, expense, income, note
                        FROM bank_ledger
                        WHERE txn_date BETWEEN %s AND %s
                        ORDER BY txn_date DESC
                    """, (from_date, to_date))
                else:
                    cur.execute("""
                        SELECT txn_date, payer, expense, income, note
                        FROM bank_ledger
                        ORDER BY txn_date DESC
                    """)
                data = cur.fetchall()
        
        if not data:
            return None
        
        columns = ['日期', '匯款人', '支出金額', '收入金額', '備註']
        df = pd.DataFrame(data, columns=columns)
        
        # 計算匯總
        total_expense = df['支出金額'].sum()
        total_income = df['收入金額'].sum()
        net_amount = total_income - total_expense
        
        # 創建 Excel 檔案
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='銀行帳本', index=False)
            
            # 添加匯總資料
            summary_data = {
                '項目': ['總收入', '總支出', '淨額'],
                '金額': [total_income, total_expense, net_amount]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='匯總', index=False)
        
        return output.getvalue()
    
    except Exception as e:
        st.error(f"❌ 匯出失敗：{e}")
        return None

# ============================================
# 新增帳本記錄 Dialog
# ============================================
@st.dialog("新增帳本記錄", width="large")
def add_ledger_dialog():
    with st.form("add_ledger_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            txn_date = st.date_input("日期 *", value=date.today(), key="add_txn_date")
            payer = st.text_input("匯款人", key="add_payer")
        
        with col2:
            # 選擇交易類型（收入或支出）
            transaction_type = st.radio(
                "交易類型 *",
                options=["收入", "支出"],
                key="add_transaction_type",
                horizontal=True
            )
            
            # 根據交易類型顯示對應的金額輸入框
            if transaction_type == "收入":
                income = st.number_input("收入金額 *", min_value=0.0, value=0.0, step=100.0, key="add_income")
                expense = 0.0
            else:  # 支出
                expense = st.number_input("支出金額 *", min_value=0.0, value=0.0, step=100.0, key="add_expense")
                income = 0.0
        
        note = st.text_area("備註", key="add_note")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not txn_date:
                st.error("日期為必填欄位！")
            elif transaction_type == "收入" and income == 0:
                st.error("請輸入收入金額！")
            elif transaction_type == "支出" and expense == 0:
                st.error("請輸入支出金額！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO bank_ledger 
                                (txn_date, payer, expense, income, note)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (txn_date, payer or None, expense, income, note or None))
                            conn.commit()
                    st.success("✅ 帳本記錄新增成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 編輯帳本記錄 Dialog
# ============================================
@st.dialog("編輯帳本記錄", width="large")
def edit_ledger_dialog(ledger_data):
    # 判斷當前記錄是收入還是支出
    current_type = "收入" if ledger_data['income'] and float(ledger_data['income']) > 0 else "支出"
    
    with st.form("edit_ledger_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            txn_date = st.date_input("日期 *", value=ledger_data['txn_date'], key="edit_txn_date")
            payer = st.text_input("匯款人", value=ledger_data['payer'] or "", key="edit_payer")
        
        with col2:
            # 選擇交易類型（收入或支出）
            transaction_type = st.radio(
                "交易類型 *",
                options=["收入", "支出"],
                index=0 if current_type == "收入" else 1,
                key="edit_transaction_type",
                horizontal=True
            )
            
            # 根據交易類型顯示對應的金額輸入框
            if transaction_type == "收入":
                income = st.number_input(
                    "收入金額 *", 
                    min_value=0.0, 
                    value=float(ledger_data['income']) if ledger_data['income'] else 0.0, 
                    step=100.0, 
                    key="edit_income"
                )
                expense = 0.0
            else:  # 支出
                expense = st.number_input(
                    "支出金額 *", 
                    min_value=0.0, 
                    value=float(ledger_data['expense']) if ledger_data['expense'] else 0.0, 
                    step=100.0, 
                    key="edit_expense"
                )
                income = 0.0
        
        note = st.text_area("備註", value=ledger_data['note'] or "", key="edit_note")
        
        col_submit, col_cancel = st.columns([1, 5])
        with col_submit:
            submitted = st.form_submit_button("✅ 更新", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            if not txn_date:
                st.error("日期為必填欄位！")
            elif transaction_type == "收入" and income == 0:
                st.error("請輸入收入金額！")
            elif transaction_type == "支出" and expense == 0:
                st.error("請輸入支出金額！")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE bank_ledger 
                                SET txn_date = %s, payer = %s, expense = %s, income = %s, note = %s
                                WHERE id = %s
                            """, (txn_date, payer or None, expense, income, note or None, ledger_data['id']))
                            conn.commit()
                    st.success("✅ 帳本記錄更新成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
        
        if cancelled:
            st.rerun()

# ============================================
# 搜尋功能（最上方）
# ============================================
search_term = st.text_input(
    "🔍 搜尋帳本記錄（可搜尋任何欄位）", 
    placeholder="輸入日期、匯款人、金額、備註等...", 
    label_visibility="collapsed"
)

st.divider()

# ============================================
# 日期選擇器和篩選選項
# ============================================
col_date_from, col_date_to, col_per_page, col_export = st.columns([1, 1, 1, 1])

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

with col_per_page:
    items_per_page = st.selectbox(
        "每頁顯示",
        options=[10, 20, 50, 100],
        index=2,  # 預設選擇 50
        key="items_per_page"
    )

# 查詢按鈕和匯出按鈕
col_query, col_export_space = st.columns([1, 1])

with col_query:
    apply_date_filter = st.button("🔍 查詢", use_container_width=True, type="primary", key="apply_date_filter")

with col_export_space:
    st.write("")  # 空行對齊
    st.write("")  # 空行對齊
    # 匯出 Excel 按鈕（使用當前的日期範圍，如果沒有套用日期篩選則匯出全部）
    export_from_date = from_date if apply_date_filter else date(1900, 1, 1)
    export_to_date = to_date if apply_date_filter else date(2100, 12, 31)
    excel_data = export_to_excel(export_from_date, export_to_date)
    
    if excel_data:
        export_filename = f"銀行帳本_{datetime.now().strftime('%Y%m%d')}.xlsx"
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
# 載入並顯示銀行帳本資料
# ============================================
try:
    # 初始化分頁狀態
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1
    
    # 如果點擊查詢按鈕或改變每頁筆數，重置到第一頁
    if ('prev_items_per_page' not in st.session_state or 
        st.session_state.get('prev_items_per_page') != items_per_page):
        st.session_state['current_page'] = 1
        st.session_state['prev_items_per_page'] = items_per_page
    
    if apply_date_filter:
        st.session_state['current_page'] = 1
    
    # 查詢銀行帳本資料
    with get_connection() as conn:
        with conn.cursor() as cur:
            if apply_date_filter:
                cur.execute("""
                    SELECT id, txn_date, payer, expense, income, note
                    FROM bank_ledger
                    WHERE txn_date BETWEEN %s AND %s
                    ORDER BY txn_date DESC
                """, (from_date, to_date))
            else:
                cur.execute("""
                    SELECT id, txn_date, payer, expense, income, note
                    FROM bank_ledger
                    ORDER BY txn_date DESC
                """)
            ledgers = cur.fetchall()
    
    if not ledgers:
        if apply_date_filter:
            st.info(f"📝 {from_date.strftime('%Y-%m-%d')} ~ {to_date.strftime('%Y-%m-%d')} 沒有帳本記錄")
        else:
            st.info("📝 目前沒有帳本記錄")
    else:
        # 轉換為 DataFrame
        columns = ['id', 'txn_date', 'payer', 'expense', 'income', 'note']
        df = pd.DataFrame(ledgers, columns=columns)
        
        # 搜尋功能
        if search_term:
            mask = df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1)
            df = df[mask]
        
        if len(df) == 0:
            st.warning(f"🔍 找不到符合條件的帳本記錄")
        else:
            # 計算匯總數字（在搜尋和分頁之前）
            total_income = df['income'].sum()
            total_expense = df['expense'].sum()
            net_amount = total_income - total_expense
            
            # 顯示匯總資訊
            if apply_date_filter:
                st.subheader(f"📊 {from_date.strftime('%Y/%m/%d')} ~ {to_date.strftime('%Y/%m/%d')} 銀行帳本")
            else:
                st.subheader(f"📊 銀行帳本（全部）")
            
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            
            with col_sum1:
                st.metric(
                    label="💰 總收入",
                    value=f"NT$ {total_income:,.0f}"
                )
            
            with col_sum2:
                st.metric(
                    label="💸 總支出",
                    value=f"NT$ {total_expense:,.0f}"
                )
            
            with col_sum3:
                # 淨額顏色：正數綠色，負數紅色
                delta_color = "normal" if net_amount >= 0 else "inverse"
                st.metric(
                    label="📈 淨額",
                    value=f"NT$ {net_amount:,.0f}",
                    delta=f"{net_amount:+,.0f}" if net_amount != 0 else None
                )
            
            st.divider()
            
            # 計算總筆數和總頁數
            total_records = len(df)
            total_pages = (total_records + items_per_page - 1) // items_per_page  # 向上取整
            
            # 確保當前頁數不超過總頁數
            if st.session_state['current_page'] > total_pages:
                st.session_state['current_page'] = total_pages if total_pages > 0 else 1
            
            st.write(f"共 {total_records} 筆帳本記錄")
            
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
            
            # 三個按鈕在同一行（表格上方）
            col_add, col_edit, col_delete, col_space = st.columns([1, 1, 1, 7])
            
            with col_add:
                if st.button("➕ 新增記錄", use_container_width=True, type="primary"):
                    add_ledger_dialog()
            
            with col_edit:
                if st.button("✏️ 編輯記錄", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_ledger_id' in st.session_state and st.session_state['selected_ledger_id'] is not None:
                        selected_id = st.session_state['selected_ledger_id']
                        if selected_id in df['id'].values:
                            selected_row = df[df['id'] == selected_id].iloc[0]
                            edit_ledger_dialog(selected_row.to_dict())
                        else:
                            st.warning("⚠️ 請先點選要編輯的記錄")
                    else:
                        st.warning("⚠️ 請先點選要編輯的記錄")
            
            with col_delete:
                if st.button("🗑️ 刪除記錄", use_container_width=True):
                    # 檢查是否有選擇資料
                    if 'selected_ledger_id' in st.session_state and st.session_state['selected_ledger_id'] is not None:
                        selected_id = st.session_state['selected_ledger_id']
                        if selected_id in df['id'].values:
                            st.session_state['confirm_delete_selected'] = selected_id
                        else:
                            st.warning("⚠️ 請先點選要刪除的記錄")
                    else:
                        st.warning("⚠️ 請先點選要刪除的記錄")
            
            st.divider()
            
            # 準備顯示用的 DataFrame
            display_df = df_paged.copy()
            display_df = display_df.rename(columns={
                'txn_date': '日期',
                'payer': '匯款人',
                'expense': '支出金額',
                'income': '收入金額',
                'note': '備註'
            })
            
            # 格式化日期和金額
            display_df['日期'] = display_df['日期'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '-')
            display_df['支出金額'] = display_df['支出金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) and x > 0 else '-')
            display_df['收入金額'] = display_df['收入金額'].apply(lambda x: f"NT$ {x:,.0f}" if pd.notna(x) and x > 0 else '-')
            
            # 顯示表格
            selection = st.dataframe(
                display_df[['日期', '匯款人', '收入金額', '支出金額', '備註']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="ledger_table"
            )
            
            # 更新選擇狀態
            if selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_row = df_paged.iloc[selected_idx]
                st.session_state['selected_ledger_id'] = selected_row['id']
            else:
                st.session_state['selected_ledger_id'] = None
            
            # 顯示已選擇的資料
            if 'selected_ledger_id' in st.session_state and st.session_state['selected_ledger_id'] is not None:
                selected_id = st.session_state['selected_ledger_id']
                if selected_id in df['id'].values:
                    selected_row = df[df['id'] == selected_id].iloc[0]
                    st.info(f"✓ 已選擇：{selected_row['txn_date']} - {selected_row['payer'] or '無匯款人'}")
                    
                    # 刪除確認（二次確認）
                    if st.session_state.get('confirm_delete_selected') == selected_id:
                        st.warning(f"⚠️ 確定要刪除帳本記錄「{selected_row['txn_date']} - {selected_row['payer'] or '無匯款人'}」嗎？此操作無法復原！")
                        col_yes, col_no, col_space2 = st.columns([1, 1, 8])
                        
                        with col_yes:
                            if st.button("✅ 確定刪除", use_container_width=True):
                                try:
                                    with get_connection() as conn:
                                        with conn.cursor() as cur:
                                            cur.execute("DELETE FROM bank_ledger WHERE id = %s", (selected_id,))
                                            conn.commit()
                                    st.success("✅ 刪除成功！")
                                    if 'confirm_delete_selected' in st.session_state:
                                        del st.session_state['confirm_delete_selected']
                                    if 'selected_ledger_id' in st.session_state:
                                        del st.session_state['selected_ledger_id']
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 刪除失敗：{e}")
                        
                        with col_no:
                            if st.button("❌ 取消", use_container_width=True):
                                if 'confirm_delete_selected' in st.session_state:
                                    del st.session_state['confirm_delete_selected']
                                st.rerun()
            
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
    st.error(f"❌ 載入銀行帳本資料失敗：{e}")

