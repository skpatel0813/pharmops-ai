import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ClipboardCheck,
  FlaskConical,
  PackageSearch,
  ShieldAlert
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { api } from "./api";
import type {
  AntibioticReview,
  InventoryItem,
  MedicationOrder,
  MedRecItem,
  SafetyEvent
} from "./types";

type Tab =
  | "overview"
  | "verification"
  | "stewardship"
  | "medrec"
  | "inventory"
  | "safety";

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value?.toLowerCase()}`}>{value}</span>;
}

function Card({
  title,
  value,
  icon
}: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="cardIcon">{icon}</div>
      <div>
        <p className="cardTitle">{title}</p>
        <h2>{value}</h2>
      </div>
    </div>
  );
}

function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<any>(null);
  const [orders, setOrders] = useState<MedicationOrder[]>([]);
  const [antibiotics, setAntibiotics] = useState<AntibioticReview[]>([]);
  const [medrec, setMedrec] = useState<MedRecItem[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [safety, setSafety] = useState<SafetyEvent[]>([]);
  const [riskChart, setRiskChart] = useState<any[]>([]);
  const [topMeds, setTopMeds] = useState<any[]>([]);
  const [inventoryRisk, setInventoryRisk] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    setLoading(true);

    const [
      overviewData,
      orderData,
      antibioticData,
      medrecData,
      inventoryData,
      safetyData,
      riskData,
      topMedData,
      inventoryRiskData
    ] = await Promise.all([
      api.overview(),
      api.medicationOrders(),
      api.antibioticReviews(),
      api.medicationReconciliation(),
      api.inventory(),
      api.safetyEvents(),
      api.riskDistribution(),
      api.topMedications(),
      api.inventoryRisk()
    ]);

    setOverview(overviewData);
    setOrders(orderData);
    setAntibiotics(antibioticData);
    setMedrec(medrecData);
    setInventory(inventoryData);
    setSafety(safetyData);
    setRiskChart(riskData);
    setTopMeds(topMedData);
    setInventoryRisk(inventoryRiskData);

    setLoading(false);
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function updateOrder(orderId: string, status: string) {
    await api.updateMedicationOrder(orderId, status);
    await loadAll();
  }

  async function updateAntibiotic(reviewId: string, status: string) {
    await api.updateAntibioticReview(reviewId, status);
    await loadAll();
  }

  async function updateMedRec(id: string, status: string) {
    await api.updateMedRec(id, status);
    await loadAll();
  }

  if (loading) {
    return (
      <div className="app">
        <h1>PharmOps AI</h1>
        <p>Loading hospital pharmacy dashboard...</p>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>PharmOps AI</h1>
        <p>Hospital Pharmacy Command Center</p>

        <button onClick={() => setTab("overview")} className={tab === "overview" ? "active" : ""}>
          Overview
        </button>
        <button onClick={() => setTab("verification")} className={tab === "verification" ? "active" : ""}>
          Verification Queue
        </button>
        <button onClick={() => setTab("stewardship")} className={tab === "stewardship" ? "active" : ""}>
          Antimicrobial Stewardship
        </button>
        <button onClick={() => setTab("medrec")} className={tab === "medrec" ? "active" : ""}>
          Medication Reconciliation
        </button>
        <button onClick={() => setTab("inventory")} className={tab === "inventory" ? "active" : ""}>
          Inventory Forecasting
        </button>
        <button onClick={() => setTab("safety")} className={tab === "safety" ? "active" : ""}>
          Safety Analytics
        </button>
      </aside>

      <main className="content">
        {tab === "overview" && (
          <>
            <div className="pageHeader">
              <h2>Executive Overview</h2>
              <p>Live operational snapshot across pharmacy verification, stewardship, reconciliation, inventory, and safety.</p>
            </div>

            <div className="cards">
              <Card title="Pending Orders" value={overview.pending_orders} icon={<ClipboardCheck />} />
              <Card title="STAT Orders" value={overview.stat_orders} icon={<Activity />} />
              <Card title="High-Risk Alerts" value={overview.high_risk_alerts} icon={<AlertTriangle />} />
              <Card title="Antibiotic Reviews" value={overview.antibiotic_reviews} icon={<FlaskConical />} />
              <Card title="Open Med Rec" value={overview.open_med_rec} icon={<ClipboardCheck />} />
              <Card title="Shortage Risks" value={overview.shortage_risks} icon={<PackageSearch />} />
              <Card title="Safety Events" value={overview.open_safety_events} icon={<ShieldAlert />} />
            </div>

            <div className="chartGrid">
              <section className="panel">
                <h3>Medication Risk Distribution</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={riskChart} dataKey="count" nameKey="risk_level" outerRadius={90} label>
                      {riskChart.map((_, index) => (
                        <Cell key={index} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </section>

              <section className="panel">
                <h3>Top Ordered Medications</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={topMeds}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="medication_name" hide />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" />
                  </BarChart>
                </ResponsiveContainer>
              </section>

              <section className="panel">
                <h3>Inventory Risk</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={inventoryRisk}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="shortage_status" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" />
                  </BarChart>
                </ResponsiveContainer>
              </section>
            </div>
          </>
        )}

        {tab === "verification" && (
          <section className="panel">
            <h2>Medication Verification Queue</h2>
            <table>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Medication</th>
                  <th>Dose</th>
                  <th>Route</th>
                  <th>Priority</th>
                  <th>Risk</th>
                  <th>Reasons</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {orders.map((order) => (
                  <tr key={order.order_id}>
                    <td>{order.patient_id}</td>
                    <td>{order.medication_name}</td>
                    <td>{order.dose} {order.dose_unit}</td>
                    <td>{order.route}</td>
                    <td><Badge value={order.priority} /></td>
                    <td>{order.risk_score}% <Badge value={order.risk_level} /></td>
                    <td>{order.risk_reasons}</td>
                    <td><Badge value={order.verification_status} /></td>
                    <td>
                      <button onClick={() => updateOrder(order.order_id, "verified")}>Verify</button>
                      <button onClick={() => updateOrder(order.order_id, "held")}>Hold</button>
                      <button onClick={() => updateOrder(order.order_id, "rejected")}>Reject</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {tab === "stewardship" && (
          <section className="panel">
            <h2>Antimicrobial Stewardship</h2>
            <table>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Antibiotic</th>
                  <th>Days</th>
                  <th>Culture</th>
                  <th>Stop Date?</th>
                  <th>IV-to-PO?</th>
                  <th>De-escalation?</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {antibiotics.map((item) => (
                  <tr key={item.review_id}>
                    <td>{item.patient_id}</td>
                    <td>{item.antibiotic_name}</td>
                    <td>{item.days_of_therapy ?? "N/A"}</td>
                    <td>{item.culture_status}</td>
                    <td>{item.stop_date_present ? "Yes" : "No"}</td>
                    <td>{item.iv_to_po_candidate ? "Yes" : "No"}</td>
                    <td>{item.deescalation_candidate ? "Yes" : "No"}</td>
                    <td><Badge value={item.review_status} /></td>
                    <td>
                      <button onClick={() => updateAntibiotic(item.review_id, "reviewed")}>Reviewed</button>
                      <button onClick={() => updateAntibiotic(item.review_id, "escalated")}>Escalate</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {tab === "medrec" && (
          <section className="panel">
            <h2>Medication Reconciliation</h2>
            <table>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Home Med</th>
                  <th>Inpatient Med</th>
                  <th>Discrepancy</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Note</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {medrec.map((item) => (
                  <tr key={item.reconciliation_id}>
                    <td>{item.patient_id}</td>
                    <td>{item.home_medication}</td>
                    <td>{item.inpatient_medication || "Not found"}</td>
                    <td>{item.discrepancy_type}</td>
                    <td><Badge value={item.severity} /></td>
                    <td><Badge value={item.status} /></td>
                    <td>{item.pharmacist_note}</td>
                    <td>
                      <button onClick={() => updateMedRec(item.reconciliation_id, "resolved")}>Resolve</button>
                      <button onClick={() => updateMedRec(item.reconciliation_id, "escalated")}>Escalate</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {medrec.length === 0 && (
              <p className="empty">
                No medication reconciliation rows loaded. Download MIMIC-IV-ED and place medrecon.csv.gz inside data/raw.
              </p>
            )}
          </section>
        )}

        {tab === "inventory" && (
          <section className="panel">
            <h2>Inventory Forecasting</h2>
            <table>
              <thead>
                <tr>
                  <th>Medication</th>
                  <th>Form</th>
                  <th>On Hand</th>
                  <th>Par</th>
                  <th>Avg Daily Use</th>
                  <th>Days On Hand</th>
                  <th>Reorder</th>
                  <th>Supplier</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {inventory.map((item) => (
                  <tr key={item.medication_id}>
                    <td>{item.medication_name}</td>
                    <td>{item.dosage_form}</td>
                    <td>{item.quantity_on_hand}</td>
                    <td>{item.par_level}</td>
                    <td>{item.avg_daily_usage}</td>
                    <td>{item.predicted_days_on_hand}</td>
                    <td>{item.reorder_recommendation}</td>
                    <td>{item.supplier}</td>
                    <td><Badge value={item.shortage_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {tab === "safety" && (
          <section className="panel">
            <h2>Medication Safety Analytics</h2>
            <table>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Medication</th>
                  <th>Event</th>
                  <th>Severity</th>
                  <th>Unit</th>
                  <th>Root Cause</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {safety.map((item) => (
                  <tr key={item.event_id}>
                    <td>{item.patient_id}</td>
                    <td>{item.medication_name}</td>
                    <td>{item.event_type}</td>
                    <td><Badge value={item.severity} /></td>
                    <td>{item.unit}</td>
                    <td>{item.root_cause}</td>
                    <td><Badge value={item.event_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;