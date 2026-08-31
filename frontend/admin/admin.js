// NetraAI Master Admin Command Center MVC Controller

let adminDataCache = null;

function initAdminPortal() {
    loadAdminDashboard();
}

function switchAdminTab(tabName) {
    const tabs = ["overview", "doctors", "patients", "simulink", "audit"];
    tabs.forEach(t => {
        const tabBtn = document.getElementById(`tabAdm${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const tabContent = document.getElementById(`adminTabContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (tabBtn) {
            tabBtn.className = (t === tabName)
                ? "px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-bold shadow-sm transition"
                : "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
        }
        if (tabContent) {
            tabContent.classList.toggle("hidden", t !== tabName);
        }
    });

    if (tabName === "overview" || tabName === "doctors" || tabName === "patients" || tabName === "audit") {
        loadAdminDashboard();
    }
}

async function loadAdminDashboard() {
    try {
        const res = await fetch(`${API_BASE}/admin/dashboard`);
        const data = await res.json();
        adminDataCache = data;

        renderAdminKPIs(data.metrics || {});
        renderDoctorManagementTable(data.doctors || []);
        renderPatientDirectoryTable(data.patients || []);
        renderAdminAuditLogs(data.audit_logs || []);
    } catch (e) {
        console.error("loadAdminDashboard error:", e);
    }
}

function renderAdminKPIs(m) {
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    };

    setVal("admTotalPatients", m.registered_patients || 0);
    setVal("admDoctorCount", m.registered_doctors || 0);
    setVal("admTotalScreenings", m.total_screenings || 0);
    setVal("admGradableRate", `${m.gradable_scans || 0} (${m.total_screenings ? ((m.gradable_scans / m.total_screenings) * 100).toFixed(1) : 100}%)`);
    setVal("admReferralRate", `${m.referral_rate_pct || 0}%`);
    setVal("admPendingReviews", m.pending_reviews || 0);
    setVal("admConfirmedReviews", m.confirmed_reviews || 0);
}

function renderDoctorManagementTable(doctors) {
    const tbody = document.getElementById("admDoctorTableBody");
    if (!tbody) return;

    if (!doctors || doctors.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">No doctor registrations found.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    doctors.forEach(d => {
        const isApproved = d.approval_status === "approved";
        const docId = d.id || d.user_id;
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition border-b border-slate-100";
        tr.innerHTML = `
            <td class="p-3">
                <div class="font-bold text-slate-800">${d.full_name || 'Dr. Specialist'}</div>
                <div class="text-[11px] text-slate-400 font-mono">${d.email || d.username || ''}</div>
            </td>
            <td class="p-3 text-slate-700 font-medium">${d.specialization || 'Ophthalmology'}</td>
            <td class="p-3 font-mono text-[11px] text-slate-600">${d.license_number || 'MCI-RET-PENDING'}</td>
            <td class="p-3 text-slate-700">${d.hospital_name || 'District Eye Hospital'}</td>
            <td class="p-3">
                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold ${isApproved ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
                    ${isApproved ? '✅ Verified & Approved' : '⏳ Pending Admin Verification'}
                </span>
            </td>
            <td class="p-3">
                ${isApproved 
                    ? `<span class="text-xs text-emerald-600 font-semibold"><i class="fa-solid fa-circle-check mr-1"></i>Active Clinician</span>`
                    : `<button onclick="handleApproveDoctor('${docId}', '${d.full_name || 'Doctor'}')" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition flex items-center space-x-1">
                        <i class="fa-solid fa-check"></i>
                        <span>Verify & Approve</span>
                    </button>`
                }
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPatientDirectoryTable(patients) {
    const tbody = document.getElementById("admPatientTableBody");
    if (!tbody) return;

    if (!patients || patients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400">No registered patients found.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    patients.forEach(p => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition border-b border-slate-100";
        tr.innerHTML = `
            <td class="p-3 font-bold text-slate-800">${p.full_name || 'Patient'}</td>
            <td class="p-3 text-slate-600">${p.age || 'N/A'} • ${p.gender || 'Female'}</td>
            <td class="p-3 text-slate-600 font-mono text-[11px]">${p.email || p.phone || 'N/A'}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700">${p.diabetes_type || 'Type 2'} (${p.diabetes_duration_years || 5}y)</span></td>
            <td class="p-3 text-slate-600 font-mono text-[11px]">${p.assigned_doctor_id ? 'Assigned to Doctor' : 'Open Pool'}</td>
            <td class="p-3">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Active</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderAdminAuditLogs(logs) {
    const listEl = document.getElementById("admAuditLogsStream");
    if (!listEl) return;

    if (!logs || logs.length === 0) {
        listEl.innerHTML = `<div class="text-xs text-slate-400 text-center py-8">No recent audit log events recorded.</div>`;
        return;
    }

    listEl.innerHTML = "";
    logs.forEach(log => {
        const item = document.createElement("div");
        item.className = "p-3 rounded-2xl bg-white border border-slate-200 flex items-start justify-between space-x-3 text-xs";
        item.innerHTML = `
            <div class="flex items-start space-x-2.5">
                <div class="w-8 h-8 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div>
                    <div class="font-bold text-slate-800">${log.title || 'System Event'}</div>
                    <div class="text-slate-500 mt-0.5">${log.description || ''}</div>
                </div>
            </div>
            <span class="text-[10px] text-slate-400 font-mono flex-shrink-0">${log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Recent'}</span>
        `;
        listEl.appendChild(item);
    });
}

async function handleApproveDoctor(docId, docName) {
    if (!confirm(`Are you sure you want to verify credentials and approve Dr. ${docName}? An official confirmation email will be dispatched to their inbox.`)) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/admin/doctor/approve/${docId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();

        if (data.status === "success") {
            showToast(`Dr. ${docName} has been verified & approved! Welcome notification sent to doctor's email.`, "success");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Doctor approval failed.", "error");
        }
    } catch (err) {
        showToast("Error approving doctor: " + err.message, "error");
    }
}

async function handleSimulinkRun() {
    const btn = document.getElementById("btnRunSimulink");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Running Simulink Solver...`;
    }

    try {
        const res = await fetch(`${API_BASE}/simulink/simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                annual_patients: 100000,
                working_days: 300,
                num_phcs: 25,
                bandwidth_mbps: 2.0,
                ai_edge_filter_rate: 0.74,
                doctor_review_time_sec: 20
            })
        });
        const result = await res.json();
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-play mr-1"></i> Run Telemedicine Simulation`;
        }

        if (result.status === "success") {
            renderSimulinkResults(result.data);
            showToast("Simulink Queuing Simulation computed across 25 rural PHCs!", "success");
        }
    } catch (e) {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-play mr-1"></i> Run Telemedicine Simulation`;
        }
        showToast("Simulation error: " + e.message, "error");
    }
}

function renderSimulinkResults(d) {
    const card = document.getElementById("simulinkResultsBox");
    if (!card) return;
    card.classList.remove("hidden");

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
    };

    setVal("simTotalDaily", d.total_daily_screenings || 333);
    setVal("simNormalFiltered", `${d.normal_mild_filtered_daily || 246} (${((d.ai_edge_filter_rate || 0.74) * 100).toFixed(0)}%)`);
    setVal("simSentToCloud", `${d.referred_to_central_cloud_daily || 87} scans/day`);
    setVal("simDocsNeededManual", d.doctors_needed_manual_baseline || 7);
    setVal("simDocsNeededNetra", d.doctors_needed_netraai || 1);
    setVal("simWorkloadReduction", `${d.workload_reduction_pct || 73.9}%`);
    setVal("simBandwidthSaved", `${d.daily_bandwidth_saved_mb || 369} MB/day`);
}
