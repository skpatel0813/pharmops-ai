from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db import engine
from app.schemas import StatusUpdate, MedRecUpdate

app = FastAPI(title="PharmOps AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_all(query: str, params: dict | None = None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def fetch_one(query: str, params: dict | None = None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        row = result.fetchone()
        return dict(row._mapping) if row else None


@app.get("/")
def root():
    return {
        "app": "PharmOps AI",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/overview")
def overview():
    query = """
    SELECT
      (SELECT COUNT(*) FROM medication_orders WHERE verification_status = 'pending') AS pending_orders,
      (SELECT COUNT(*) FROM medication_orders WHERE priority = 'STAT') AS stat_orders,
      (SELECT COUNT(*) FROM medication_orders WHERE risk_level = 'high') AS high_risk_alerts,
      (SELECT COUNT(*) FROM antibiotic_reviews WHERE review_status = 'needs_review') AS antibiotic_reviews,
      (SELECT COUNT(*) FROM medication_reconciliation WHERE status = 'open') AS open_med_rec,
      (SELECT COUNT(*) FROM pharmacy_inventory WHERE shortage_status IN ('critical', 'low')) AS shortage_risks,
      (SELECT COUNT(*) FROM safety_events WHERE event_status = 'open') AS open_safety_events
    """
    return fetch_one(query)


@app.get("/api/medication-orders")
def medication_orders(
    status: str | None = None,
    risk_level: str | None = None,
    priority: str | None = None
):
    conditions = []
    params = {}

    if status:
        conditions.append("verification_status = :status")
        params["status"] = status

    if risk_level:
        conditions.append("risk_level = :risk_level")
        params["risk_level"] = risk_level

    if priority:
        conditions.append("priority = :priority")
        params["priority"] = priority

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
    SELECT
        order_id,
        patient_id,
        admission_id,
        medication_name,
        dose,
        dose_unit,
        route,
        frequency,
        priority,
        verification_status,
        pharmacist_note,
        risk_score,
        risk_level,
        risk_reasons,
        start_time,
        stop_time
    FROM medication_orders
    {where_clause}
    ORDER BY risk_score DESC NULLS LAST, start_time DESC NULLS LAST
    LIMIT 250
    """

    return fetch_all(query, params)


@app.patch("/api/medication-orders/{order_id}")
def update_medication_order(order_id: str, payload: StatusUpdate):
    allowed = {"pending", "verified", "held", "rejected"}

    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    with engine.begin() as conn:
        result = conn.execute(
            text("""
            UPDATE medication_orders
            SET verification_status = :status,
                pharmacist_note = COALESCE(:note, pharmacist_note)
            WHERE order_id = :order_id
            """),
            {
                "status": payload.status,
                "note": payload.pharmacist_note,
                "order_id": order_id
            }
        )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Medication order not found")

    return {"message": "Medication order updated", "order_id": order_id}


@app.get("/api/antibiotic-reviews")
def antibiotic_reviews(status: str | None = None):
    params = {}
    where_clause = ""

    if status:
        where_clause = "WHERE review_status = :status"
        params["status"] = status

    query = f"""
    SELECT
        review_id,
        patient_id,
        admission_id,
        antibiotic_name,
        start_time,
        stop_time,
        days_of_therapy,
        culture_status,
        stop_date_present,
        iv_to_po_candidate,
        deescalation_candidate,
        review_status,
        pharmacist_note
    FROM antibiotic_reviews
    {where_clause}
    ORDER BY
      deescalation_candidate DESC,
      days_of_therapy DESC NULLS LAST
    LIMIT 250
    """

    return fetch_all(query, params)


@app.patch("/api/antibiotic-reviews/{review_id}")
def update_antibiotic_review(review_id: str, payload: StatusUpdate):
    allowed = {"needs_review", "reviewed", "escalated"}

    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    with engine.begin() as conn:
        result = conn.execute(
            text("""
            UPDATE antibiotic_reviews
            SET review_status = :status,
                pharmacist_note = COALESCE(:note, pharmacist_note)
            WHERE review_id = :review_id
            """),
            {
                "status": payload.status,
                "note": payload.pharmacist_note,
                "review_id": review_id
            }
        )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Antibiotic review not found")

    return {"message": "Antibiotic review updated", "review_id": review_id}


@app.get("/api/medication-reconciliation")
def medication_reconciliation(status: str | None = None):
    params = {}
    where_clause = ""

    if status:
        where_clause = "WHERE status = :status"
        params["status"] = status

    query = f"""
    SELECT
        reconciliation_id,
        patient_id,
        admission_id,
        home_medication,
        inpatient_medication,
        discrepancy_type,
        severity,
        status,
        pharmacist_note
    FROM medication_reconciliation
    {where_clause}
    ORDER BY
      CASE severity
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        ELSE 3
      END,
      reconciliation_id
    LIMIT 250
    """

    return fetch_all(query, params)


@app.patch("/api/medication-reconciliation/{reconciliation_id}")
def update_med_rec(reconciliation_id: str, payload: MedRecUpdate):
    allowed = {"open", "resolved", "escalated"}

    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    with engine.begin() as conn:
        result = conn.execute(
            text("""
            UPDATE medication_reconciliation
            SET status = :status,
                pharmacist_note = COALESCE(:note, pharmacist_note)
            WHERE reconciliation_id = :reconciliation_id
            """),
            {
                "status": payload.status,
                "note": payload.pharmacist_note,
                "reconciliation_id": reconciliation_id
            }
        )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Medication reconciliation item not found")

    return {
        "message": "Medication reconciliation item updated",
        "reconciliation_id": reconciliation_id
    }


@app.get("/api/inventory")
def inventory(shortage_status: str | None = None):
    params = {}
    where_clause = ""

    if shortage_status:
        where_clause = "WHERE shortage_status = :shortage_status"
        params["shortage_status"] = shortage_status

    query = f"""
    SELECT
        medication_id,
        medication_name,
        dosage_form,
        quantity_on_hand,
        par_level,
        avg_daily_usage,
        predicted_days_on_hand,
        reorder_recommendation,
        unit_cost,
        supplier,
        shortage_status
    FROM pharmacy_inventory
    {where_clause}
    ORDER BY predicted_days_on_hand ASC NULLS LAST
    LIMIT 250
    """

    return fetch_all(query, params)


@app.get("/api/safety-events")
def safety_events():
    query = """
    SELECT
        event_id,
        patient_id,
        admission_id,
        medication_name,
        event_type,
        severity,
        unit,
        root_cause,
        event_status
    FROM safety_events
    ORDER BY
      CASE severity
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        ELSE 3
      END
    LIMIT 250
    """

    return fetch_all(query)


@app.get("/api/charts/risk-distribution")
def risk_distribution():
    query = """
    SELECT risk_level, COUNT(*) AS count
    FROM medication_orders
    GROUP BY risk_level
    ORDER BY count DESC
    """

    return fetch_all(query)


@app.get("/api/charts/top-medications")
def top_medications():
    query = """
    SELECT medication_name, COUNT(*) AS count
    FROM medication_orders
    WHERE medication_name IS NOT NULL
    GROUP BY medication_name
    ORDER BY count DESC
    LIMIT 10
    """

    return fetch_all(query)


@app.get("/api/charts/inventory-risk")
def inventory_risk():
    query = """
    SELECT shortage_status, COUNT(*) AS count
    FROM pharmacy_inventory
    GROUP BY shortage_status
    ORDER BY count DESC
    """

    return fetch_all(query)