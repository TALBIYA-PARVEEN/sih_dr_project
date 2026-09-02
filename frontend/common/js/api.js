// NetraAI API Configuration & Network Layer
const LIVE_BACKEND_URL = "https://sih-dr-project.onrender.com";
const API_BASE = window.location.protocol.startsWith("http")
    ? (["5500", "3000", "8080"].includes(window.location.port) ? "http://127.0.0.1:5050/api" : "/api")
    : "http://127.0.0.1:5050/api";

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
