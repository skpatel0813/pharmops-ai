const API_BASE = "http://127.0.0.1:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  overview: () => request<any>("/overview"),

  medicationOrders: () => request<any[]>("/medication-orders"),

  updateMedicationOrder: (orderId: string, status: string, note?: string) =>
    request(`/medication-orders/${orderId}`, {
      method: "PATCH",
      body: JSON.stringify({
        status,
        pharmacist_note: note || null
      })
    }),

  antibioticReviews: () => request<any[]>("/antibiotic-reviews"),

  updateAntibioticReview: (reviewId: string, status: string, note?: string) =>
    request(`/antibiotic-reviews/${reviewId}`, {
      method: "PATCH",
      body: JSON.stringify({
        status,
        pharmacist_note: note || null
      })
    }),

  medicationReconciliation: () => request<any[]>("/medication-reconciliation"),

  updateMedRec: (id: string, status: string, note?: string) =>
    request(`/medication-reconciliation/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status,
        pharmacist_note: note || null
      })
    }),

  inventory: () => request<any[]>("/inventory"),

  safetyEvents: () => request<any[]>("/safety-events"),

  riskDistribution: () => request<any[]>("/charts/risk-distribution"),

  topMedications: () => request<any[]>("/charts/top-medications"),

  inventoryRisk: () => request<any[]>("/charts/inventory-risk")
};