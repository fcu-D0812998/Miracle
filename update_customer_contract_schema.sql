-- ============================================
-- 更新客戶與合約管理頁面所需的欄位
-- ============================================

-- 1. 更新 customers 表
ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS sales_company_id INT REFERENCES companies(id),
ADD COLUMN IF NOT EXISTS note TEXT,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';

-- 2. 更新 contracts 表
ALTER TABLE contracts
ADD COLUMN IF NOT EXISTS model VARCHAR(50),              -- 機型（一個合約一種機型）
ADD COLUMN IF NOT EXISTS term_months INT,                -- 合約期數（月）
ADD COLUMN IF NOT EXISTS end_date DATE,                  -- 合約結束日
ADD COLUMN IF NOT EXISTS sales_commission NUMERIC(10,2), -- 業務佣金
ADD COLUMN IF NOT EXISTS maint_commission NUMERIC(10,2); -- 維護佣金

-- 3. 移除不需要的欄位（如果存在）
ALTER TABLE contracts DROP COLUMN IF EXISTS base_rent;

-- 4. 新增索引
CREATE INDEX IF NOT EXISTS idx_customers_sales_company ON customers(sales_company_id);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);

-- 完成提示
SELECT '✅ 資料庫結構更新完成！' AS status;
