// NetraAI API Configuration & Network Layer
const LIVE_BACKEND_URL = "https://netraai-backend.onrender.com";
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "5000")
    ? (window.location.port === "5000" ? "/api" : "http://127.0.0.1:5000/api")
    : `${LIVE_BACKEND_URL}/api`;

const ApiClient = {
    get: async (endpoint) => {
        const token = localStorage.getItem("netra_token");
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE}${endpoint}`, { headers });
        return await res.json();
    },

    post: async (endpoint, payload) => {
        const token = localStorage.getItem("netra_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers,
            body: JSON.stringify(payload)
        });
        return await res.json();
    },

    postForm: async (endpoint, formData) => {
        const token = localStorage.getItem("netra_token");
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers,
            body: formData
        });
        return await res.json();
    }
};
