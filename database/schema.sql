DROP TABLE IF EXISTS safety_events CASCADE;
DROP TABLE IF EXISTS pharmacy_inventory CASCADE;
DROP TABLE IF EXISTS pharmacy_sales CASCADE;
DROP TABLE IF EXISTS medication_reconciliation CASCADE;
DROP TABLE IF EXISTS antibiotic_reviews CASCADE;
DROP TABLE IF EXISTS medication_orders CASCADE;
DROP TABLE IF EXISTS admissions CASCADE;
DROP TABLE IF EXISTS patients CASCADE;

CREATE TABLE patients (
    patient_id TEXT PRIMARY KEY,
    gender TEXT,
    anchor_age INT,
    anchor_year INT
);

CREATE TABLE admissions (
    admission_id TEXT PRIMARY KEY,
    patient_id TEXT REFERENCES patients(patient_id),
    admit_time TIMESTAMP NULL,
    discharge_time TIMESTAMP NULL,
    admission_type TEXT,
    insurance TEXT,
    language TEXT,
    marital_status TEXT,
    race TEXT
);

CREATE TABLE medication_orders (
    order_id TEXT PRIMARY KEY,
    patient_id TEXT,
    admission_id TEXT,
    medication_name TEXT,
    dose TEXT,
    dose_unit TEXT,
    route TEXT,
    frequency TEXT,
    start_time TIMESTAMP NULL,
    stop_time TIMESTAMP NULL,
    priority TEXT,
    verification_status TEXT DEFAULT 'pending',
    pharmacist_note TEXT,
    risk_score NUMERIC,
    risk_level TEXT,
    risk_reasons TEXT
);

CREATE TABLE antibiotic_reviews (
    review_id TEXT PRIMARY KEY,
    patient_id TEXT,
    admission_id TEXT,
    antibiotic_name TEXT,
    start_time TIMESTAMP NULL,
    stop_time TIMESTAMP NULL,
    days_of_therapy NUMERIC,
    culture_status TEXT,
    stop_date_present BOOLEAN,
    iv_to_po_candidate BOOLEAN,
    deescalation_candidate BOOLEAN,
    review_status TEXT DEFAULT 'needs_review',
    pharmacist_note TEXT
);

CREATE TABLE medication_reconciliation (
    reconciliation_id TEXT PRIMARY KEY,
    patient_id TEXT,
    admission_id TEXT,
    home_medication TEXT,
    inpatient_medication TEXT,
    discrepancy_type TEXT,
    severity TEXT,
    status TEXT DEFAULT 'open',
    pharmacist_note TEXT
);

CREATE TABLE pharmacy_sales (
    sale_id SERIAL PRIMARY KEY,
    sale_date TIMESTAMP,
    medication_name TEXT,
    quantity_sold NUMERIC
);

CREATE TABLE pharmacy_inventory (
    medication_id TEXT PRIMARY KEY,
    medication_name TEXT,
    dosage_form TEXT,
    quantity_on_hand INT,
    par_level INT,
    avg_daily_usage NUMERIC,
    predicted_days_on_hand NUMERIC,
    reorder_recommendation INT,
    unit_cost NUMERIC,
    supplier TEXT,
    shortage_status TEXT
);

CREATE TABLE safety_events (
    event_id TEXT PRIMARY KEY,
    patient_id TEXT,
    admission_id TEXT,
    medication_name TEXT,
    event_type TEXT,
    severity TEXT,
    unit TEXT,
    root_cause TEXT,
    event_status TEXT DEFAULT 'open'
);

CREATE INDEX idx_med_orders_status ON medication_orders(verification_status);
CREATE INDEX idx_med_orders_risk ON medication_orders(risk_level);
CREATE INDEX idx_abx_status ON antibiotic_reviews(review_status);
CREATE INDEX idx_inventory_shortage ON pharmacy_inventory(shortage_status);
CREATE INDEX idx_medrec_status ON medication_reconciliation(status);