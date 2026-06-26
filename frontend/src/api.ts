import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api";

export const api = {
  getOverview: async () => {
    const res = await axios.get(`${API_BASE}/overview`);
    return res.data;
  },

  getMedicationOrders: async () => {
    const res = await axios.get(`${API_BASE}/medication-orders`);
    return res.data;
  },

  getAntibioticReviews: async () => {
    const res = await axios.get(`${API_BASE}/antibiotic-reviews`);
    return res.data;
  },

  verifyOrder: async (orderId: string) => {
    const res = await axios.post(`${API_BASE}/medication-orders/${orderId}/verify`);
    return res.data;
  },

  holdOrder: async (orderId: string) => {
    const res = await axios.post(`${API_BASE}/medication-orders/${orderId}/hold`);
    return res.data;
  }
};