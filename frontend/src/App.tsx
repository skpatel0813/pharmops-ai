import { useEffect, useState } from "react";
import { api } from "./api";
import "./App.css";

type Order = {
  order_id: string;
  patient_id: string;
  medication_name: string;
  dose: string;
  route: string;
  frequency: string;
  priority: string;
  verification_status: string;
  risk_score: number;
  risk_level: string;
  risk_reasons: string;
};

function App() {
  const [overview, setOverview] = useState<any>(null);
  const [orders, setOrders] = useState<Order[]>([]);

  async function loadData() {
    const overviewData = await api.getOverview();
    const orderData = await api.getMedicationOrders();

    setOverview(overviewData);
    setOrders(orderData);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function verify(orderId: string) {
    await api.verifyOrder(orderId);
    await loadData();
  }

  async function hold(orderId: string) {
    await api.holdOrder(orderId);
    await loadData();
  }

  return (
    <div className="app">
      <h1>PharmOps AI</h1>
      <p>Hospital Pharmacy Operations Dashboard</p>

      {overview && (
        <div className="cards">
          <div className="card">
            <h3>Pending Orders</h3>
            <p>{overview.pendingOrders}</p>
          </div>

          <div className="card">
            <h3>STAT Orders</h3>
            <p>{overview.statOrders}</p>
          </div>

          <div className="card">
            <h3>High-Risk Alerts</h3>
            <p>{overview.highRiskAlerts}</p>
          </div>

          <div className="card">
            <h3>Antibiotic Reviews</h3>
            <p>{overview.antibioticReviews}</p>
          </div>
        </div>
      )}

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
              <td>{order.dose}</td>
              <td>{order.route}</td>
              <td>{order.priority}</td>
              <td>
                {order.risk_score}% / {order.risk_level}
              </td>
              <td>{order.risk_reasons}</td>
              <td>{order.verification_status}</td>
              <td>
                <button onClick={() => verify(order.order_id)}>Verify</button>
                <button onClick={() => hold(order.order_id)}>Hold</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;