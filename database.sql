-- ============================================
-- 基礎資料表
-- ============================================

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    tax_id VARCHAR(20),
    contact VARCHAR(50),
    phone VARCHAR(50),
    email VARCHAR(100),
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) CHECK (type IN ('sales', 'maintenance')),
    name VARCHAR(100) NOT NULL,
    split_rate NUMERIC(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 合約與設備
-- ============================================

CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    kind VARCHAR(20) CHECK (kind IN ('RENT','BUYOUT')),
    start_date DATE NOT NULL,
    pay_mode_months INT DEFAULT 1,  -- 1=月繳, 3=季繳, 6=半年, 12=年繳
    base_rent NUMERIC(12,2) DEFAULT 0,
    bw_included INT DEFAULT 0,
    color_included INT DEFAULT 0,
    bw_rate NUMERIC(8,2) DEFAULT 0,
    color_rate NUMERIC(8,2) DEFAULT 0,
    sales_company_id INT REFERENCES companies(id),
    maint_company_id INT REFERENCES companies(id),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    contract_id INT REFERENCES contracts(id) ON DELETE CASCADE,
    serial_no VARCHAR(50) UNIQUE,
    model VARCHAR(50),
    purchase_cost NUMERIC(12,2) DEFAULT 0,
    extra_cost NUMERIC(12,2) DEFAULT 0,
    amort_method VARCHAR(20) DEFAULT 'straight_line',
    amort_end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id) ON DELETE CASCADE,
    period_start DATE,
    period_end DATE,
    bw_count INT DEFAULT 0,
    color_count INT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 服務與未出帳
-- ============================================

CREATE TABLE service_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) DEFAULT '次',
    price NUMERIC(10,2) DEFAULT 0,
    taxable BOOLEAN DEFAULT TRUE,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE pending_charges (
    id SERIAL PRIMARY KEY,
    contract_id INT REFERENCES contracts(id) ON DELETE CASCADE,
    device_id INT REFERENCES devices(id),
    charge_type VARCHAR(20) CHECK (charge_type IN ('BASE','OVERAGE','SERVICE','MISC_PASS')),
    qty NUMERIC(10,2) DEFAULT 0,
    rate NUMERIC(10,2) DEFAULT 0,
    amount NUMERIC(12,2) DEFAULT 0,
    period DATE,
    note TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 出帳 (發票 / 應收)
-- ============================================

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    invoice_no VARCHAR(50),
    date DATE DEFAULT CURRENT_DATE,
    period_start DATE,
    period_end DATE,
    total NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INT REFERENCES invoices(id) ON DELETE CASCADE,
    device_id INT REFERENCES devices(id),
    item_type VARCHAR(20) CHECK (item_type IN ('BASE','OVERAGE','SERVICE','MISC_PASS')),
    qty NUMERIC(10,2),
    rate NUMERIC(10,2),
    amount NUMERIC(12,2),
    note TEXT
);

CREATE TABLE ar_ledger (
    id SERIAL PRIMARY KEY,
    invoice_id INT REFERENCES invoices(id) ON DELETE CASCADE,
    open_amount NUMERIC(12,2) DEFAULT 0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aging_bucket VARCHAR(20)
);

-- ============================================
-- 收款與沖帳
-- ============================================

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    date DATE DEFAULT CURRENT_DATE,
    method VARCHAR(50),
    amount NUMERIC(12,2),
    fee_amount NUMERIC(10,2) DEFAULT 0,
    ref_no VARCHAR(100),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_allocations (
    id SERIAL PRIMARY KEY,
    payment_id INT REFERENCES payments(id) ON DELETE CASCADE,
    invoice_id INT REFERENCES invoices(id) ON DELETE CASCADE,
    applied_amount NUMERIC(12,2) DEFAULT 0
);

-- ============================================
-- 支出與人事
-- ============================================

CREATE TABLE staff (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    dept VARCHAR(50),
    monthly_salary NUMERIC(10,2),
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    type VARCHAR(50),
    amount NUMERIC(12,2),
    vendor VARCHAR(100),
    staff_id INT REFERENCES staff(id),
    device_id INT REFERENCES devices(id),
    pass_through BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 使用者
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) CHECK (role IN ('admin','accountant','sales','maintenance')) DEFAULT 'sales',
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
