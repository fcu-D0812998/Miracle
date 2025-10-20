-- ===========================================
-- 1️⃣ 建立共用 ENUM 型別（繳費狀況）
-- ===========================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status_enum') THEN
        CREATE TYPE payment_status_enum AS ENUM ('未收', '部分收款', '已收款');
    END IF;
END$$;

-- ===========================================
-- 2️⃣ 客戶表 customers（改為輸入業務姓名）
-- ===========================================
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(50) UNIQUE NOT NULL,     -- 客戶代碼
    name VARCHAR(100) NOT NULL,                    -- 客戶名稱
    contact_name VARCHAR(100),                     -- 聯絡人
    mobile VARCHAR(20),
    phone VARCHAR(20),
    address TEXT,
    email VARCHAR(100),
    tax_id VARCHAR(20),                            -- 統編
    sales_rep_name VARCHAR(100),                   -- 負責業務（姓名）
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===========================================
-- 3️⃣ 公司表 companies
-- ===========================================
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    company_code VARCHAR(50) UNIQUE NOT NULL,      -- 公司代碼
    name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100),
    mobile VARCHAR(20),
    phone VARCHAR(20),
    address TEXT,
    email VARCHAR(100),
    tax_id VARCHAR(20),
    sales_rep VARCHAR(100),                        -- 負責業務
    is_sales BOOLEAN DEFAULT FALSE,                -- 是否為業務公司
    is_service BOOLEAN DEFAULT FALSE,              -- 是否為維護公司
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 4️⃣ 租賃合約 contracts_leasing
-- ===========================================
CREATE TABLE contracts_leasing (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(50) UNIQUE NOT NULL,     -- 合約編號
    customer_code VARCHAR(50) REFERENCES customers(customer_code),
    customer_name VARCHAR(100),
    start_date DATE NOT NULL,                      -- 合約起始日
    model VARCHAR(100),                            -- 機型
    quantity INT DEFAULT 1,                        -- 台數
    monthly_rent NUMERIC(12,2),                    -- 月租金
    payment_cycle_months INT DEFAULT 1,            -- 每幾個月繳一次（例：1=月繳、3=季繳）
    overprint VARCHAR(100),                        -- 超印描述（或費率）
    contract_months INT,                           -- 合約期數（月）
    sales_company_code VARCHAR(50) REFERENCES companies(company_code),
    sales_amount NUMERIC(12,2),
    service_company_code VARCHAR(50) REFERENCES companies(company_code),
    service_amount NUMERIC(12,2),
    sales_payment_status buyout_payment_status_enum DEFAULT '未付款', -- 是否出帳
    service_payment_status buyout_payment_status_enum DEFAULT'未付款', -- 是否出帳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- ===========================================
-- 5️⃣ 買斷合約 contracts_buyout
-- ===========================================
CREATE TABLE contracts_buyout (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(50) UNIQUE NOT NULL,
    customer_code VARCHAR(50) REFERENCES customers(customer_code),
    customer_name VARCHAR(100),
    deal_date DATE NOT NULL,                       -- 成交日期
    deal_amount NUMERIC(12,2),                     -- 成交金額
    sales_company_code VARCHAR(50) REFERENCES companies(company_code),
    sales_amount NUMERIC(12,2),
    service_company_code VARCHAR(50) REFERENCES companies(company_code),
    service_amount NUMERIC(12,2),
    sales_payment_status buyout_payment_status_enum DEFAULT '未付款', -- 是否出帳
    service_payment_status buyout_payment_status_enum DEFAULT'未付款', -- 是否出帳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 6️⃣ 租賃應收帳款 ar_leasing
-- ===========================================
CREATE TABLE ar_leasing (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(50) REFERENCES contracts_leasing(contract_code),
    customer_code VARCHAR(50) REFERENCES customers(customer_code),
    customer_name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    total_rent NUMERIC(12,2),
    fee NUMERIC(12,2),                              -- 手續費
    received_amount NUMERIC(12,2) DEFAULT 0,        -- 實際收到金額
    payment_status payment_status_enum DEFAULT '未收',  -- 繳費狀況（ENUM）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 7️⃣ 買斷應收帳款 ar_buyout
-- ===========================================
CREATE TABLE ar_buyout (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(50) REFERENCES contracts_buyout(contract_code),
    customer_code VARCHAR(50) REFERENCES customers(customer_code),
    customer_name VARCHAR(100),
    deal_date DATE,
    total_amount NUMERIC(12,2),
    fee NUMERIC(12,2),
    received_amount NUMERIC(12,2) DEFAULT 0,
    payment_status payment_status_enum DEFAULT '未收',  -- ENUM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 8️⃣ 服務費用表 service_expense
-- ===========================================
CREATE TABLE service_expense (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(50),
    customer_code VARCHAR(50),
    customer_name VARCHAR(100),
    service_date DATE,                             -- 服務日期
    confirm_date DATE,                             -- 確認日期（核准入帳）
    service_type VARCHAR(50),                      -- 服務類型（維修/保養）
    repair_company_code VARCHAR(50) REFERENCES companies(company_code),
    total_amount NUMERIC(12,2),
    payment_status payment_status_enum DEFAULT '未收', -- 改成 ENUM，一致化
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
