// NetraAI API Configuration & Network Layer
const API_BASE = "http://127.0.0.1:5000/api";

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
