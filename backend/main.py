import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

app = FastAPI(title="PharmOps AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/overview")
def overview():
    with engine.connect() as conn:
        pending_orders = conn.execute(text("""
            SELECT COUNT(*) FROM medication_orders
            WHERE verification_status = 'pending'
        """)).scalar()

        stat_orders = conn.execute(text("""
            SELECT COUNT(*) FROM medication_orders
            WHERE priority = 'STAT'
        """)).scalar()

        high_risk = conn.execute(text("""
            SELECT COUNT(*) FROM medication_orders
            WHERE risk_level = 'high'
        """)).scalar()

        abx_reviews = conn.execute(text("""
            SELECT COUNT(*) FROM antibiotic_reviews
            WHERE review_status = 'needs_review'
        """)).scalar()

        med_rec_open = conn.execute(text("""
            SELECT COUNT(*) FROM medication_reconciliation
            WHERE status = 'open'
        """)).scalar()

    return {
        "pendingOrders": pending_orders,
        "statOrders": stat_orders,
        "highRiskAlerts": high_risk,
        "antibioticReviews": abx_reviews,
        "openMedicationReconciliation": med_rec_open
    }

@app.get("/api/medication-orders")
def medication_orders():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                order_id,
                patient_id,
                admission_id,
                medication_name,
                dose,
                route,
                frequency,
                priority,
                verification_status,
                risk_score,
                risk_level,
                risk_reasons
            FROM medication_orders
            ORDER BY risk_score DESC NULLS LAST
            LIMIT 100
        """))

        return [dict(row._mapping) for row in result]

@app.get("/api/antibiotic-reviews")
def antibiotic_reviews():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                review_id,
                patient_id,
                admission_id,
                antibiotic_name,
                days_of_therapy,
                culture_status,
                stop_date_present,
                iv_to_po_candidate,
                deescalation_candidate,
                review_status
            FROM antibiotic_reviews
            ORDER BY days_of_therapy DESC NULLS LAST
            LIMIT 100
        """))

        return [dict(row._mapping) for row in result]

@app.post("/api/medication-orders/{order_id}/verify")
def verify_order(order_id: str):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE medication_orders
            SET verification_status = 'verified'
            WHERE order_id = :order_id
        """), {"order_id": order_id})

    return {"message": "Order verified", "order_id": order_id}

@app.post("/api/medication-orders/{order_id}/hold")
def hold_order(order_id: str):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE medication_orders
            SET verification_status = 'held'
            WHERE order_id = :order_id
        """), {"order_id": order_id})

    return {"message": "Order held", "order_id": order_id}