export type MedicationOrder = {
  order_id: string;
  patient_id: string;
  admission_id: string;
  medication_name: string;
  dose: string;
  dose_unit: string;
  route: string;
  frequency: string;
  priority: string;
  verification_status: string;
  pharmacist_note: string | null;
  risk_score: number;
  risk_level: string;
  risk_reasons: string;
};

export type AntibioticReview = {
  review_id: string;
  patient_id: string;
  admission_id: string;
  antibiotic_name: string;
  days_of_therapy: number | null;
  culture_status: string;
  stop_date_present: boolean;
  iv_to_po_candidate: boolean;
  deescalation_candidate: boolean;
  review_status: string;
  pharmacist_note: string | null;
};

export type MedRecItem = {
  reconciliation_id: string;
  patient_id: string;
  admission_id: string;
  home_medication: string;
  inpatient_medication: string | null;
  discrepancy_type: string;
  severity: string;
  status: string;
  pharmacist_note: string | null;
};

export type InventoryItem = {
  medication_id: string;
  medication_name: string;
  dosage_form: string;
  quantity_on_hand: number;
  par_level: number;
  avg_daily_usage: number;
  predicted_days_on_hand: number;
  reorder_recommendation: number;
  unit_cost: number;
  supplier: string;
  shortage_status: string;
};

export type SafetyEvent = {
  event_id: string;
  patient_id: string;
  admission_id: string;
  medication_name: string;
  event_type: string;
  severity: string;
  unit: string;
  root_cause: string;
  event_status: string;
};