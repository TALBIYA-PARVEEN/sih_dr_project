// NetraAI Tele-Ophthalmology Fullstack Frontend Logic
const API_BASE = window.location.origin.includes("5000") ? "/api" : "http://localhost:5000/api";

// Reactive State
let currentUser = JSON.parse(localStorage.getItem("netra_user") || "null");
let authToken = localStorage.getItem("netra_token") || null;
let activeSessionId = localStorage.getItem("netra_active_session_id") || null;
let navigationHistory = ["home"];
let selectedFile = null;
let doctorQueue = [];
let currentDoctorSession = null;
let tempRegisterEmail = null;

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    setupUploadHandlers();
    fetchDoctors();
    
    const initialHash = window.location.hash.replace("#", "");
    const validPages = ["home", "models", "login", "register", "patient", "doctor", "admin"];
    
    if (initialHash && validPages.includes(initialHash)) {
        navigateTo(initialHash, false);
    } else {
        navigateTo("home", false);
    }

    // Restore active screening session if available on refresh
    if (activeSessionId) {
        restoreLastSession(activeSessionId);
    }

    window.addEventListener("popstate", (event) => {
        if (event.state && event.state.page) {
            navigateTo(event.state.page, false);
        } else {
            const hash = window.location.hash.replace("#", "");
            navigateTo(hash && validPages.includes(hash) ? hash : "home", false);
        }
    });
});

// -----------------------------------------------------------------------------
// 1. Navigation & Browser History
// -----------------------------------------------------------------------------
function navigateTo(pageId, pushState = true) {
    const pages = ["home", "patient", "doctor", "admin", "models", "login", "register"];
    
    pages.forEach(p => {
        const el = document.getElementById("page" + p.charAt(0).toUpperCase() + p.slice(1));
        if (el) el.classList.add("hidden");
        const navEl = document.getElementById("navLink" + p.charAt(0).toUpperCase() + p.slice(1));
        if (navEl) navEl.classList.remove("bg-indigo-900", "text-white");
    });

    const activePage = document.getElementById("page" + pageId.charAt(0).toUpperCase() + pageId.slice(1));
    if (activePage) activePage.classList.remove("hidden");

    const activeNav = document.getElementById("navLink" + pageId.charAt(0).toUpperCase() + pageId.slice(1));
    if (activeNav) activeNav.classList.add("bg-indigo-900", "text-white");

    if (pushState) {
        history.pushState({ page: pageId }, "", "#" + pageId);
        navigationHistory.push(pageId);
    }

    updateNavbarForPage(pageId);

    if (pageId === "doctor") loadDoctorQueue();
    if (pageId === "admin") loadAdminDashboard();
    if (pageId === "patient" && currentUser) {
        updatePatientProfileUI();
        loadPatientHistory();
        loadPatientChat();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        navigateTo("home");
    }
}

function openLoginModal(role) {
    navigateTo("login");
    const sub = document.getElementById("loginSubtitle");
    if (sub) {
        if (role === "doctor") sub.innerText = "Sign in to Ophthalmologist Clinical Workstation";
        else if (role === "admin") sub.innerText = "Sign in to District Master Admin Command Center";
        else sub.innerText = "Sign in to Patient Screening Dashboard";
    }
}

function openRegisterModal(role) {
    navigateTo("register");
    setRegisterRole(role || "patient");
}

// -----------------------------------------------------------------------------
// 2. Strict Public vs. Authenticated Navbar Updates
// -----------------------------------------------------------------------------
function updateNavbarForPage(pageId) {
    const publicNav = document.getElementById("publicNavLinks");
    const authNav = document.getElementById("authNavLinks");
    const userBar = document.getElementById("userProfileBar");
    const guestBtns = document.getElementById("guestAuthButtons");

    const patientNav = document.getElementById("patientNavSection");
    const doctorNav = document.getElementById("doctorNavSection");
    const adminNav = document.getElementById("adminNavSection");

    const isPublicPage = (pageId === "home" || pageId === "models" || pageId === "login" || pageId === "register");

    if (isPublicPage || !currentUser || !authToken) {
        publicNav.classList.remove("hidden");
        authNav.classList.add("hidden");
        userBar.classList.add("hidden");
        guestBtns.classList.remove("hidden");

        patientNav.classList.add("hidden");
        doctorNav.classList.add("hidden");
        adminNav.classList.add("hidden");
    } else {
        publicNav.classList.add("hidden");
        authNav.classList.remove("hidden");
        userBar.classList.remove("hidden");
        guestBtns.classList.add("hidden");

        document.getElementById("navUserName").innerText = currentUser.full_name || currentUser.username;
        document.getElementById("navUserRole").innerText = currentUser.role.toUpperCase();
        document.getElementById("navAvatar").innerText = (currentUser.full_name || currentUser.username).charAt(0).toUpperCase();

        patientNav.classList.add("hidden");
        doctorNav.classList.add("hidden");
        adminNav.classList.add("hidden");

        if (currentUser.role === "doctor") {
            doctorNav.classList.remove("hidden");
        } else if (currentUser.role === "admin") {
            adminNav.classList.remove("hidden");
        } else {
            patientNav.classList.remove("hidden");
        }
    }
}

function handleLogout() {
    localStorage.removeItem("netra_user");
    localStorage.removeItem("netra_token");
    localStorage.removeItem("netra_active_session_id");
    currentUser = null;
    authToken = null;
    activeSessionId = null;
    showToast("Signed out successfully.", "info");
    navigateTo("home");
}

function fillLogin(uname, pass) {
    document.getElementById("loginUsername").value = uname;
    document.getElementById("loginPassword").value = pass;
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (data.status === "success") {
            currentUser = data.user;
            authToken = data.token;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            localStorage.setItem("netra_token", authToken);
            showToast(data.message, "success");

            if (currentUser.role === "doctor") navigateTo("doctor");
            else if (currentUser.role === "admin") navigateTo("admin");
            else navigateTo("patient");
        } else {
            showToast(data.error || "Login failed.", "error");
        }
    } catch (err) {
        showToast("Error connecting to server: " + err.message, "error");
    }
}

// -----------------------------------------------------------------------------
// 3. Registration & Real Email OTP Verification
// -----------------------------------------------------------------------------
let regRole = "patient";
function setRegisterRole(role) {
    regRole = role;
    const tabP = document.getElementById("tabRegPatient");
    const tabD = document.getElementById("tabRegDoctor");
    const docFields = document.getElementById("doctorExtraFields");
    const patFields = document.getElementById("patientExtraFields");

    if (role === "doctor") {
        tabD.className = "py-2 text-xs font-bold rounded-lg bg-white shadow text-emerald-700 transition";
        tabP.className = "py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-indigo-700 transition";
        docFields.classList.remove("hidden");
        if (patFields) patFields.classList.add("hidden");
    } else {
        tabP.className = "py-2 text-xs font-bold rounded-lg bg-white shadow text-indigo-700 transition";
        tabD.className = "py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-indigo-700 transition";
        docFields.classList.add("hidden");
        if (patFields) patFields.classList.remove("hidden");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const payload = {
        full_name: document.getElementById("regFullName").value.trim(),
        username: document.getElementById("regUsername").value.trim(),
        age: parseInt(document.getElementById("regAge").value) || 50,
        gender: document.getElementById("regGender").value,
        email: document.getElementById("regEmail").value.trim(),
        password: document.getElementById("regPassword").value.trim(),
        phone: document.getElementById("regPhone").value.trim(),
        role: regRole,
        diabetes_type: document.getElementById("regDiabetesType") ? document.getElementById("regDiabetesType").value : "Type 2",
        diabetes_duration_years: document.getElementById("regDiabetesDuration") ? parseInt(document.getElementById("regDiabetesDuration").value) || 5 : 5,
        specialization: document.getElementById("regSpecialization") ? document.getElementById("regSpecialization").value.trim() : "",
        license_number: document.getElementById("regLicense") ? document.getElementById("regLicense").value.trim() : "",
        hospital_name: document.getElementById("regHospital") ? document.getElementById("regHospital").value.trim() : ""
    };

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.status === "success") {
            tempRegisterEmail = payload.email;
            currentUser = data.user;
            authToken = data.token;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            localStorage.setItem("netra_token", authToken);

            document.getElementById("modalOtp").classList.remove("hidden");
            document.getElementById("otpModalSubtext").innerHTML = `We have sent a 6-digit verification code to <b>${payload.email}</b>. Please check your inbox.`;
            document.getElementById("otpInputCode").value = "";
            document.getElementById("otpInputCode").focus();
            showToast(`Verification code sent to ${payload.email}`, "success");
        } else {
            showToast(data.error || "Registration failed.", "error");
        }
    } catch (err) {
        showToast("Error connecting to server: " + err.message, "error");
    }
}

async function handleVerifyOtp() {
    const code = document.getElementById("otpInputCode").value.trim();
    if (!code || code.length < 6) {
        showToast("Please enter the 6-digit code received in your email.", "warning");
        return;
    }

    try {
        const targetEmail = tempRegisterEmail || (currentUser ? currentUser.email : "");
        const res = await fetch(`${API_BASE}/auth/verify-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: targetEmail, otp: code })
        });
        const data = await res.json();

        if (data.status === "success") {
            closeOtpModal();
            currentUser = data.user;
            authToken = data.token;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            localStorage.setItem("netra_token", authToken);

            if (currentUser && currentUser.role === "doctor") {
                const approval = currentUser.approval_status || currentUser.status;
                if (approval === "pending_approval") {
                    showToast("Email verified! Your doctor registration is submitted to District Master Admin for approval.", "info");
                    navigateTo("landing");
                } else {
                    showToast("Email verified! Welcome Dr. " + currentUser.full_name, "success");
                    navigateTo("doctor");
                }
            } else if (currentUser && currentUser.role === "admin") {
                navigateTo("admin");
            } else {
                showToast("Email verified successfully! Welcome to NetraAI.", "success");
                navigateTo("patient");
            }
        } else {
            showToast(data.error || "Invalid verification code. Please check your email.", "error");
        }
    } catch (err) {
        showToast("Verification error: " + err.message, "error");
    }
}

async function resendOtpCode() {
    const targetEmail = tempRegisterEmail || (currentUser ? currentUser.email : "");
    if (!targetEmail) {
        showToast("Please enter your email to receive code.", "warning");
        return;
    }
    const btn = document.getElementById("btnResendOtp");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Sending...`;
    }
    try {
        const res = await fetch(`${API_BASE}/auth/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: targetEmail })
        });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`New verification code sent to ${targetEmail}. Please check your Inbox / Spam folder.`, "success");
        } else {
            showToast(data.error || "Failed to resend code.", "error");
        }
    } catch (e) {
        showToast("Network error: " + e.message, "error");
    } finally {
        if (btn) {
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-rotate-right mr-1"></i> Resend Code`;
            }, 5000);
        }
    }
}

function closeOtpModal() {
    document.getElementById("modalOtp").classList.add("hidden");
}

function showForgotPasswordModal() {
    const email = prompt("Enter your registered email address to receive an OTP code:");
    if (email) {
        fetch(`${API_BASE}/auth/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        }).then(r => r.json()).then(d => {
            if (d.status === "success") {
                tempRegisterEmail = email;
                document.getElementById("modalOtp").classList.remove("hidden");
                document.getElementById("otpModalSubtext").innerHTML = `Verification code sent to <b>${email}</b>.`;
                document.getElementById("otpInputCode").value = "";
                showToast("Verification code dispatched to your email.", "info");
            } else {
                alert(d.error || "Failed to send code.");
            }
        });
    }
}

// -----------------------------------------------------------------------------
// 4. Patient Profile UI & Edit Management
// -----------------------------------------------------------------------------
function updatePatientProfileUI() {
    if (!currentUser) return;
    const name = currentUser.full_name || currentUser.username;
    const age = currentUser.age || 50;
    const gender = currentUser.gender || "Female";
    const email = currentUser.email || "";
    const phone = currentUser.phone || "Not provided";
    const diabType = currentUser.diabetes_type || "Type 2 Diabetes";
    const diabDur = currentUser.diabetes_duration_years || 5;

    const nameEl = document.getElementById("patientCardFullName");
    if (nameEl) nameEl.innerText = name;

    const ageGenEl = document.getElementById("patientCardAgeGender");
    if (ageGenEl) ageGenEl.innerText = `Age: ${age} • ${gender} • ${diabType} (${diabDur} yrs)`;

    const contactEl = document.getElementById("patientCardContact");
    if (contactEl) contactEl.innerText = `Email: ${email} • Phone: ${phone}`;

    const attachedName = document.getElementById("labelPatientAttached");
    if (attachedName) attachedName.innerText = `Screening for: ${name}`;

    const attachedAgeGen = document.getElementById("labelPatientAgeGender");
    if (attachedAgeGen) attachedAgeGen.innerText = `Age: ${age} • Gender: ${gender} • ${diabType}`;
}

function openEditProfileModal() {
    if (!currentUser) return;
    document.getElementById("editProfileName").value = currentUser.full_name || "";
    document.getElementById("editProfilePhone").value = currentUser.phone || "";

    const patFields = document.getElementById("editPatientFields");
    const docFields = document.getElementById("editDoctorFields");
    const modalTitle = document.getElementById("editProfileModalTitle");

    if (currentUser.role === "doctor") {
        if (modalTitle) modalTitle.innerHTML = `<i class="fa-solid fa-user-doctor text-emerald-600"></i><span>Edit Doctor Profile</span>`;
        if (patFields) patFields.classList.add("hidden");
        if (docFields) docFields.classList.remove("hidden");
        if (document.getElementById("editProfileSpecialization")) document.getElementById("editProfileSpecialization").value = currentUser.specialization || "";
        if (document.getElementById("editProfileLicense")) document.getElementById("editProfileLicense").value = currentUser.license_number || "";
        if (document.getElementById("editProfileHospital")) document.getElementById("editProfileHospital").value = currentUser.hospital_name || "";
    } else {
        if (modalTitle) modalTitle.innerHTML = `<i class="fa-solid fa-user-pen text-indigo-600"></i><span>Edit Patient Profile</span>`;
        if (patFields) patFields.classList.remove("hidden");
        if (docFields) docFields.classList.add("hidden");
        if (document.getElementById("editProfileAge")) document.getElementById("editProfileAge").value = currentUser.age || 50;
        if (document.getElementById("editProfileGender")) document.getElementById("editProfileGender").value = currentUser.gender || "Female";
        if (document.getElementById("editProfileDiabetesType")) document.getElementById("editProfileDiabetesType").value = currentUser.diabetes_type || "Type 2";
        if (document.getElementById("editProfileDiabetesDuration")) document.getElementById("editProfileDiabetesDuration").value = currentUser.diabetes_duration_years || 5;
    }

    document.getElementById("modalEditProfile").classList.remove("hidden");
}

function closeEditProfileModal() {
    document.getElementById("modalEditProfile").classList.add("hidden");
}

async function handleSaveProfile(e) {
    e.preventDefault();
    if (!currentUser) return;

    const payload = {
        full_name: document.getElementById("editProfileName").value.trim(),
        phone: document.getElementById("editProfilePhone").value.trim()
    };

    if (currentUser.role === "doctor") {
        payload.specialization = document.getElementById("editProfileSpecialization").value.trim();
        payload.license_number = document.getElementById("editProfileLicense").value.trim();
        payload.hospital_name = document.getElementById("editProfileHospital").value.trim();
    } else {
        payload.age = parseInt(document.getElementById("editProfileAge").value) || 50;
        payload.gender = document.getElementById("editProfileGender").value;
        payload.diabetes_type = document.getElementById("editProfileDiabetesType").value;
        payload.diabetes_duration_years = parseInt(document.getElementById("editProfileDiabetesDuration").value) || 5;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/profile/${currentUser.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.status === "success") {
            currentUser = data.user;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            updatePatientProfileUI();
            closeEditProfileModal();
            showToast("Profile details updated successfully!", "success");
        } else {
            showToast(data.error || "Update failed.", "error");
        }
    } catch (err) {
        showToast("Error updating profile: " + err.message, "error");
    }
}

// -----------------------------------------------------------------------------
// 5. In-Dashboard Tabs: Patient Dashboard & Past Reports
// -----------------------------------------------------------------------------
function switchPatientTab(tab) {
    const tabScreening = document.getElementById("tabPatientScreening");
    const tabHistory = document.getElementById("tabPatientHistory");
    const tabChat = document.getElementById("tabPatientChat");

    const contentScreening = document.getElementById("patientTabScreeningContent");
    const contentHistory = document.getElementById("patientTabHistoryContent");
    const contentChat = document.getElementById("patientTabChatContent");

    tabScreening.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
    tabHistory.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
    tabChat.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";

    contentScreening.classList.add("hidden");
    contentHistory.classList.add("hidden");
    contentChat.classList.add("hidden");

    if (tab === "history") {
        tabHistory.className = "px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
        contentHistory.classList.remove("hidden");
        loadPatientHistory();
    } else if (tab === "chat") {
        tabChat.className = "px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
        contentChat.classList.remove("hidden");
        loadPatientChat();
    } else {
        tabScreening.className = "px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
        contentScreening.classList.remove("hidden");
    }
}

async function loadPatientHistory() {
    if (!currentUser) return;
    const tbody = document.getElementById("patientHistoryTableBody");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/patient/history/${currentUser.id}`);
        const data = await res.json();
        const history = data.history || [];

        tbody.innerHTML = "";
        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">No previous screenings found. Upload your first retinal scan to see records here.</td></tr>`;
            return;
        }

        history.forEach(s => {
            const tr = document.createElement("tr");
            const dateStr = s.created_at ? new Date(s.created_at).toLocaleDateString("en-IN", {
                day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
            }) : "Recent";
            
            const scanId = s.screening_id || s.id;
            const sev = s.final_severity_name || s.severity_name || (s.prediction ? s.prediction.severity_name : "Moderate NPDR");
            const qual = s.quality_status || (s.quality_assessment ? s.quality_assessment.quality_label : "GOOD");
            const docName = s.doctor_name || s.assigned_doctor_name || "Dr. S. Sharma, MD";
            const docStatus = s.clinical_status || s.review_status || (s.clinician_review ? s.clinician_review.status : "Pending Review");
            const pdfUrl = s.pdf_report_url || `${API_BASE}/report/${scanId}/pdf`;

            tr.innerHTML = `
                <td class="p-3 font-mono text-slate-500">${dateStr}</td>
                <td class="p-3 font-semibold text-slate-800">${sev}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded-full font-bold ${qual === 'GOOD' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">${qual}</span></td>
                <td class="p-3 text-slate-600">${docName}</td>
                <td class="p-3 font-bold ${docStatus === 'Confirmed' ? 'text-emerald-600' : (docStatus === 'Overruled' ? 'text-rose-600' : 'text-amber-600')}">${docStatus}</td>
                <td class="p-3 flex items-center space-x-2">
                    <button onclick="restoreLastSession('${scanId}')" class="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold transition">View Scan</button>
                    <a href="${pdfUrl}" target="_blank" class="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold transition">PDF</a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("History load error", e);
    }
}

// -----------------------------------------------------------------------------
// 6. Patient Image Upload & Dual-AI Diagnostic Pipeline (Persists on Refresh)
// -----------------------------------------------------------------------------
function setupUploadHandlers() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("border-indigo-500", "bg-indigo-50/50");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-indigo-500", "bg-indigo-50/50");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-indigo-500", "bg-indigo-50/50");
        if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
    });
}

function handleFileSelect(file) {
    selectedFile = file;
    document.getElementById("fileNamePreview").innerText = file.name;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById("imgPreview").src = e.target.result;
        document.getElementById("previewContainer").classList.remove("hidden");
    };
    reader.readAsDataURL(file);
}

async function runPatientScreening() {
    if (!selectedFile) {
        alert("Please select a retinal fundus scan first.");
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    if (currentUser) {
        formData.append("patient_user_id", currentUser.id);
        formData.append("patient_name", currentUser.full_name || currentUser.username);
        formData.append("patient_age", currentUser.age || 50);
        formData.append("patient_gender", currentUser.gender || "Female");
    }

    document.getElementById("patientLoadingState").classList.remove("hidden");
    document.getElementById("rejectionCard").classList.add("hidden");
    document.getElementById("patientResultContainer").classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE}/screen`, {
            method: "POST",
            body: formData
        });
        const result = await res.json();
        document.getElementById("patientLoadingState").classList.add("hidden");

        if (result.status === "rejected") {
            document.getElementById("rejectionCard").classList.remove("hidden");
            document.getElementById("rejectionReasonText").innerText = result.message;
            return;
        }

        if (result.status === "success") {
            activeSessionId = result.session_id;
            localStorage.setItem("netra_active_session_id", activeSessionId);
            renderPatientResults(result.data);
            showToast("Dual AI Screening complete! Results saved.", "success");
            loadPatientHistory();
        }
    } catch (err) {
        document.getElementById("patientLoadingState").classList.add("hidden");
        showToast("Screening error: " + err.message, "error");
    }
}

async function restoreLastSession(sessionId) {
    try {
        const res = await fetch(`${API_BASE}/session/${sessionId}`);
        const data = await res.json();
        if (data.status === "success" && data.data) {
            renderPatientResults(data.data);
            switchPatientTab("screening");
        }
    } catch (e) {}
}

function renderPatientResults(data) {
    activeSessionId = data.id;
    document.getElementById("patientResultContainer").classList.remove("hidden");

    const qual = data.quality_assessment;
    document.getElementById("resQualityBadge").innerText = qual.quality_label;
    document.getElementById("resQualityScore").innerText = qual.quality_score + "%";
    document.getElementById("resFocusScore").innerText = `Focus: ${qual.blur_score} • FOV: ${(qual.fov_ratio * 100).toFixed(1)}%`;

    const pred = data.prediction;
    document.getElementById("resSeverityName").innerText = pred.severity_name;
    document.getElementById("resConfidence").innerText = `Confidence: ${(pred.confidence * 100).toFixed(1)}%`;
    document.getElementById("resTriageAction").innerText = pred.triage_action;

    const refBadge = document.getElementById("resReferralBadge");
    if (pred.is_referable) {
        refBadge.className = "mt-1 inline-block px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700";
        refBadge.innerText = "🚨 REFERRAL RECOMMENDED";
    } else {
        refBadge.className = "mt-1 inline-block px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700";
        refBadge.innerText = "🟢 ROUTINE ANNUAL SCREENING";
    }

    document.getElementById("viewImgOriginal").src = `${API_BASE}/files/${data.id}/original`;
    document.getElementById("viewImgVessels").src = `${API_BASE}/files/${data.id}/vessels`;
    document.getElementById("viewImgLesions").src = `${API_BASE}/files/${data.id}/lesions`;
    document.getElementById("viewImgGradcam").src = `${API_BASE}/files/${data.id}/gradcam`;

    const bio = data.biomarkers;
    document.getElementById("bioRedCount").innerText = bio.red_dots_count;
    document.getElementById("bioYellowCount").innerText = bio.yellow_dots_count;
    document.getElementById("bioWhiteCount").innerText = bio.white_dots_count;
    document.getElementById("bioOpticDisc").innerText = bio.optic_disc_coord || "(N/A)";
    document.getElementById("labelVessels").innerText = `2. Vessels (${bio.vessel_density_pct}%)`;

    const rev = data.clinician_review;
    document.getElementById("patientDocStatus").innerText = rev.status;
    document.getElementById("patientDocNotes").innerText = rev.notes || `Assigned to ${data.assigned_doctor_name || 'Ophthalmologist'}.`;
    
    const assignedDocNameEl = document.getElementById("patientAssignedDoctorName");
    if (assignedDocNameEl && data.assigned_doctor_name) {
        assignedDocNameEl.innerText = data.assigned_doctor_name;
    }
}

// -----------------------------------------------------------------------------
// 7. Doctor Workstation & Queue
// -----------------------------------------------------------------------------
function switchDoctorTab(tab) {
    const tabWorkstation = document.getElementById("tabDoctorWorkstation");
    const tabChat = document.getElementById("tabDoctorChat");
    const contentWorkstation = document.getElementById("doctorTabWorkstationContent");
    const contentChat = document.getElementById("doctorTabChatContent");

    if (tab === "chat") {
        tabChat.className = "px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
        tabWorkstation.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
        contentChat.classList.remove("hidden");
        contentWorkstation.classList.add("hidden");
        loadDoctorChat();
    } else {
        tabWorkstation.className = "px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
        tabChat.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
        contentWorkstation.classList.remove("hidden");
        contentChat.classList.add("hidden");
    }
}

async function loadDoctorQueue() {
    const docId = currentUser && currentUser.role === "doctor" ? currentUser.id : "all";
    try {
        const res = await fetch(`${API_BASE}/doctor/queue/${docId}`);
        const data = await res.json();
        doctorQueue = data.screenings || [];
        document.getElementById("doctorQueueCount").innerText = doctorQueue.length;

        const list = document.getElementById("doctorQueueList");
        list.innerHTML = "";

        if (doctorQueue.length === 0) {
            list.innerHTML = `<div class="text-xs text-slate-400 text-center py-6">No pending patient scans in your queue. (Your own scans are routed to independent peers).</div>`;
            return;
        }

        doctorQueue.forEach((s) => {
            const isRef = s.prediction && s.prediction.is_referable;
            const item = document.createElement("div");
            item.className = "p-3 rounded-2xl border border-slate-200 hover:border-emerald-500 cursor-pointer transition bg-white space-y-1";
            item.onclick = () => selectDoctorPatient(s);

            item.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="font-semibold text-xs text-slate-800">${s.patient_name || 'Patient'}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold ${isRef ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}">
                        ${s.prediction ? s.prediction.severity_name.split('(')[0] : 'Ungradable'}
                    </span>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-400">
                    <span>Age: ${s.patient_age || 'N/A'}</span>
                    <span class="font-medium text-slate-600">${s.clinician_review.status}</span>
                </div>
            `;
            list.appendChild(item);
        });

        if (doctorQueue.length > 0) selectDoctorPatient(doctorQueue[0]);
    } catch (e) {
        console.error("Queue load error", e);
    }
}

function selectDoctorPatient(session) {
    currentDoctorSession = session;
    activeSessionId = session.id;

    document.getElementById("doctorStationEmpty").classList.add("hidden");
    document.getElementById("doctorStationContent").classList.remove("hidden");

    document.getElementById("docPatientName").innerText = `Patient: ${session.patient_name || 'Anonymous'}`;
    document.getElementById("docPatientMeta").innerText = `Age: ${session.patient_age || 'N/A'} • Gender: ${session.patient_gender || 'N/A'}`;
    document.getElementById("docAIStatusBadge").innerText = session.prediction ? session.prediction.severity_name : "Ungradable";

    document.getElementById("docScanOrig").src = `${API_BASE}/files/${session.id}/original`;
    document.getElementById("docScanVessels").src = `${API_BASE}/files/${session.id}/vessels`;
    document.getElementById("docScanLesions").src = `${API_BASE}/files/${session.id}/lesions`;
    document.getElementById("docScanGradcam").src = `${API_BASE}/files/${session.id}/gradcam`;

    document.getElementById("docSelectStatus").value = session.clinician_review.status || "Confirmed";
    document.getElementById("docInputNotes").value = session.clinician_review.notes || "";
}

async function submitDoctorSignOff() {
    if (!currentDoctorSession) return;

    const status = document.getElementById("docSelectStatus").value;
    const notes = document.getElementById("docInputNotes").value;
    const docName = currentUser && currentUser.role === "doctor" ? currentUser.full_name : "Dr. S. Sharma, MD";
    const docId = currentUser ? currentUser.id : null;

    try {
        const res = await fetch(`${API_BASE}/review/${currentDoctorSession.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, notes, reviewed_by: docName, doctor_id: docId })
        });
        const data = await res.json();

        if (data.status === "success") {
            showToast("Clinical sign-off recorded & patient notified!", "success");
            loadDoctorQueue();
        } else {
            showToast(data.error || "Sign-off error.", "error");
        }
    } catch (e) {
        showToast("Error submitting sign-off: " + e.message, "error");
    }
}

// -----------------------------------------------------------------------------
// 8. In-Dashboard Tele-Consultation Messaging Handlers
// -----------------------------------------------------------------------------
async function loadPatientChat() {
    if (!currentUser) return;
    const partnerId = currentUser.assigned_doctor_id || "doc_demo";
    try {
        const res = await fetch(`${API_BASE}/messages/thread/${currentUser.id}/${partnerId}`);
        const data = await res.json();
        const stream = document.getElementById("patientChatMessagesStream");
        if (!stream) return;
        stream.innerHTML = "";

        if (!data.messages || data.messages.length === 0) {
            stream.innerHTML = `<div class="text-xs text-slate-400 text-center py-10">No messages yet. Send a message to your assigned ophthalmologist below.</div>`;
            return;
        }

        data.messages.forEach(m => {
            const isMe = m.sender_id === currentUser.id;
            const bubble = document.createElement("div");
            bubble.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;
            bubble.innerHTML = `
                <div class="max-w-xs p-3 rounded-2xl text-xs ${isMe ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white border text-slate-800 rounded-bl-none shadow-xs'}">
                    <div class="font-semibold text-[10px] opacity-75 mb-0.5">${m.sender_name} (${m.sender_role})</div>
                    <div>${m.content}</div>
                </div>
            `;
            stream.appendChild(bubble);
        });
        stream.scrollTop = stream.scrollHeight;
    } catch (e) {}
}

async function handlePatientSendMessage(e) {
    e.preventDefault();
    if (!currentUser) return;
    const input = document.getElementById("inputPatientMessage");
    const content = input.value.trim();
    if (!content) return;

    const recipientId = currentUser.assigned_doctor_id || "doc_demo";
    try {
        const res = await fetch(`${API_BASE}/messages/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sender_id: currentUser.id,
                recipient_id: recipientId,
                content: content,
                screening_id: activeSessionId
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = "";
            loadPatientChat();
        }
    } catch (err) {
        showToast("Error sending message: " + err.message, "error");
    }
}

async function loadDoctorChat() {
    if (!currentUser) return;
    const partnerId = currentDoctorSession ? currentDoctorSession.patient_user_id : "patient_demo";
    try {
        const res = await fetch(`${API_BASE}/messages/thread/${currentUser.id}/${partnerId}`);
        const data = await res.json();
        const stream = document.getElementById("doctorChatMessagesStream");
        if (!stream) return;
        stream.innerHTML = "";

        if (!data.messages || data.messages.length === 0) {
            stream.innerHTML = `<div class="text-xs text-slate-400 text-center py-10">No messages yet with this patient.</div>`;
            return;
        }

        data.messages.forEach(m => {
            const isMe = m.sender_id === currentUser.id;
            const bubble = document.createElement("div");
            bubble.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;
            bubble.innerHTML = `
                <div class="max-w-xs p-3 rounded-2xl text-xs ${isMe ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-white border text-slate-800 rounded-bl-none shadow-xs'}">
                    <div class="font-semibold text-[10px] opacity-75 mb-0.5">${m.sender_name} (${m.sender_role})</div>
                    <div>${m.content}</div>
                </div>
            `;
            stream.appendChild(bubble);
        });
        stream.scrollTop = stream.scrollHeight;
    } catch (e) {}
}

async function handleDoctorSendMessage(e) {
    e.preventDefault();
    if (!currentUser) return;
    const input = document.getElementById("inputDoctorMessage");
    const content = input.value.trim();
    if (!content) return;

    const recipientId = currentDoctorSession ? currentDoctorSession.patient_user_id : "patient_demo";
    try {
        const res = await fetch(`${API_BASE}/messages/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sender_id: currentUser.id,
                recipient_id: recipientId,
                content: content,
                screening_id: activeSessionId
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = "";
            loadDoctorChat();
        }
    } catch (err) {
        showToast("Error sending message: " + err.message, "error");
    }
}

// -----------------------------------------------------------------------------
// 9. Master Admin Portal & District Healthcare Administration
// -----------------------------------------------------------------------------
function switchAdminTab(tabName) {
    const tabs = ['overview', 'doctors', 'patients', 'simulink', 'audit'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tabAdm${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const content = document.getElementById(`adminTabContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (btn && content) {
            if (t === tabName) {
                btn.className = "px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-bold shadow-sm transition";
                content.classList.remove("hidden");
            } else {
                btn.className = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition";
                content.classList.add("hidden");
            }
        }
    });
}

async function loadAdminDashboard() {
    try {
        const res = await fetch(`${API_BASE}/admin/dashboard`);
        const data = await res.json();

        // 1. KPI Metrics
        const m = data.metrics;
        document.getElementById("admTotalPatients").innerText = m.registered_patients;
        document.getElementById("admDoctorCount").innerText = m.registered_doctors;
        document.getElementById("admTotalScreenings").innerText = m.total_screenings;
        document.getElementById("admGradableCount").innerText = m.gradable_scans;
        document.getElementById("admReferralRate").innerText = m.referral_rate_pct + "%";

        // 2. Retinopathy Disease Prevalence Distribution
        const sev = data.severity_distribution || {};
        const totalCases = Math.max(1, m.total_screenings);
        const grades = [
            { key: "Level 0 (No DR)", countEl: "prevCount0", barEl: "prevBar0" },
            { key: "Level 1 (Mild NPDR)", countEl: "prevCount1", barEl: "prevBar1" },
            { key: "Level 2 (Moderate NPDR)", countEl: "prevCount2", barEl: "prevBar2" },
            { key: "Level 3 (Severe NPDR)", countEl: "prevCount3", barEl: "prevBar3" },
            { key: "Level 4 (PDR)", countEl: "prevCount4", barEl: "prevBar4" }
        ];
        grades.forEach(g => {
            const cnt = sev[g.key] || 0;
            const pct = Math.round((cnt / totalCases) * 100);
            const countEl = document.getElementById(g.countEl);
            const barEl = document.getElementById(g.barEl);
            if (countEl) countEl.innerText = `${cnt} cases (${pct}%)`;
            if (barEl) barEl.style.width = `${pct}%`;
        });

        // 3. Populate Doctors Management Table
        const docTbody = document.getElementById("adminDoctorsTableBody");
        if (docTbody) {
            docTbody.innerHTML = "";
            if (data.doctors && data.doctors.length > 0) {
                data.doctors.forEach(doc => {
                    const tr = document.createElement("tr");
                    const docId = doc.id || doc.user_id;
                    const approval = doc.approval_status || (doc.active_status ? "approved" : "pending_approval");
                    
                    let statusBadge = "";
                    let actionBtns = "";

                    if (approval === "pending_approval") {
                        statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 animate-pulse"><i class="fa-solid fa-hourglass-half mr-1"></i> Pending Approval</span>`;
                        actionBtns = `
                            <button onclick="adminApproveDoctor('${docId}')" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold rounded-lg transition shadow-2xs">
                                <i class="fa-solid fa-check mr-0.5"></i> Approve
                            </button>
                            <button onclick="adminBlacklistDoctor('${docId}')" class="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-white text-[11px] font-bold rounded-lg transition shadow-2xs">
                                <i class="fa-solid fa-ban mr-0.5"></i> Blacklist
                            </button>
                            <button onclick="adminRemoveDoctor('${docId}')" class="px-2 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-bold rounded-lg border border-rose-200 transition">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        `;
                    } else if (approval === "approved") {
                        statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800"><i class="fa-solid fa-circle-check mr-1"></i> Active Doctor</span>`;
                        actionBtns = `
                            <button onclick="adminBlacklistDoctor('${docId}')" class="px-2.5 py-1 bg-slate-100 hover:bg-amber-100 hover:text-amber-800 text-slate-700 text-[11px] font-semibold rounded-lg border transition">
                                <i class="fa-solid fa-ban mr-0.5"></i> Blacklist
                            </button>
                            <button onclick="adminRemoveDoctor('${docId}')" class="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-bold rounded-lg border border-rose-200 transition">
                                <i class="fa-solid fa-trash mr-0.5"></i> Remove
                            </button>
                        `;
                    } else { // blacklisted
                        statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800"><i class="fa-solid fa-ban mr-1"></i> Blacklisted</span>`;
                        actionBtns = `
                            <button onclick="adminApproveDoctor('${docId}')" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold rounded-lg transition shadow-2xs">
                                <i class="fa-solid fa-check mr-0.5"></i> Re-Approve
                            </button>
                            <button onclick="adminRemoveDoctor('${docId}')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold rounded-lg transition shadow-2xs">
                                <i class="fa-solid fa-trash mr-0.5"></i> Delete
                            </button>
                        `;
                    }

                    tr.innerHTML = `
                        <td class="p-3 font-semibold text-slate-800">
                            <div class="flex items-center space-x-2">
                                <div class="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                                    <i class="fa-solid fa-user-doctor"></i>
                                </div>
                                <span>${doc.full_name}</span>
                            </div>
                        </td>
                        <td class="p-3 font-mono text-purple-700 font-bold">${doc.license_number || 'MCI-VERIFIED'}</td>
                        <td class="p-3 text-slate-600">${doc.specialization || 'Vitreo-Retina Specialist'}</td>
                        <td class="p-3 text-slate-600">${doc.hospital_name || 'District Apex Hospital'}</td>
                        <td class="p-3 text-slate-500">${doc.email || 'N/A'}<br><span class="text-[10px] font-mono">${doc.phone || '+91 9876543210'}</span></td>
                        <td class="p-3">${statusBadge}</td>
                        <td class="p-3">
                            <div class="flex items-center space-x-1.5 flex-wrap gap-y-1">
                                ${actionBtns}
                            </div>
                        </td>
                    `;
                    docTbody.appendChild(tr);
                });
            } else {
                docTbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400 font-medium">No doctors registered yet. New doctor registrations will appear here for Master Admin approval.</td></tr>`;
            }
        }

        // 4. Populate Patients Directory Table
        const patTbody = document.getElementById("adminPatientsTableBody");
        if (patTbody) {
            patTbody.innerHTML = "";
            if (data.patients && data.patients.length > 0) {
                data.patients.forEach(pat => {
                    const tr = document.createElement("tr");
                    const patId = pat.id || pat.user_id;
                    const isBlacklisted = pat.status === "blacklisted";
                    const dateFormatted = pat.created_at ? new Date(pat.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "31 Aug 2026";
                    
                    let patStatusBadge = isBlacklisted 
                        ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">Blacklisted</span>`
                        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Active</span>`;

                    let patActionBtns = isBlacklisted
                        ? `
                            <button onclick="adminActivatePatient('${patId}')" class="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-[11px] font-bold rounded-lg border border-emerald-200 transition">
                                <i class="fa-solid fa-check mr-0.5"></i> Restore
                            </button>
                            <button onclick="adminRemovePatient('${patId}')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold rounded-lg transition shadow-2xs">
                                <i class="fa-solid fa-trash mr-0.5"></i> Remove
                            </button>
                        `
                        : `
                            <button onclick="adminBlacklistPatient('${patId}')" class="px-2.5 py-1 bg-slate-100 hover:bg-amber-100 hover:text-amber-800 text-slate-700 text-[11px] font-semibold rounded-lg border transition">
                                <i class="fa-solid fa-ban mr-0.5"></i> Blacklist
                            </button>
                            <button onclick="adminRemovePatient('${patId}')" class="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-bold rounded-lg border border-rose-200 transition">
                                <i class="fa-solid fa-trash mr-0.5"></i> Remove
                            </button>
                        `;

                    tr.innerHTML = `
                        <td class="p-3 font-semibold text-slate-800">
                            <div class="flex items-center space-x-2">
                                <div class="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                                    <i class="fa-solid fa-user"></i>
                                </div>
                                <span>${pat.full_name}</span>
                            </div>
                        </td>
                        <td class="p-3 text-slate-600">${pat.age || 22} Yrs • ${pat.gender || 'Female'}</td>
                        <td class="p-3"><span class="px-2 py-0.5 bg-amber-50 text-amber-800 rounded font-semibold text-[11px] border border-amber-200">${pat.diabetes_type || 'Type 2'} (${pat.diabetes_duration_years || 5} yrs)</span></td>
                        <td class="p-3 text-slate-500">${pat.email || 'user@gmail.com'}<br><span class="text-[10px] font-mono">${pat.phone || '+91 9876543210'}</span></td>
                        <td class="p-3">${patStatusBadge}</td>
                        <td class="p-3 text-slate-500 font-mono text-[11px]">${dateFormatted}</td>
                        <td class="p-3">
                            <div class="flex items-center space-x-1.5">
                                ${patActionBtns}
                            </div>
                        </td>
                    `;
                    patTbody.appendChild(tr);
                });
            } else {
                patTbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400 font-medium">No registered patients in directory.</td></tr>`;
            }
        }

        // 5. Populate System Audit Table
        const auditTbody = document.getElementById("adminAuditTableBody");
        if (auditTbody) {
            auditTbody.innerHTML = "";
            if (data.audit_logs && data.audit_logs.length > 0) {
                data.audit_logs.forEach(evt => {
                    const tr = document.createElement("tr");
                    const timeFormatted = evt.timestamp ? new Date(evt.timestamp).toLocaleString("en-IN", { hour12: true, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "31 Aug 2026, 10:15 am";
                    let badgeClass = "bg-purple-100 text-purple-800";
                    let icon = "fa-id-badge";
                    if (evt.type === "CLINICAL_SIGNOFF") {
                        badgeClass = "bg-emerald-100 text-emerald-800";
                        icon = "fa-signature";
                    }
                    tr.innerHTML = `
                        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}"><i class="fa-solid ${icon} mr-1"></i> ${evt.type}</span></td>
                        <td class="p-3 font-semibold text-slate-800">${evt.title}</td>
                        <td class="p-3 text-slate-600">${evt.description}</td>
                        <td class="p-3 font-mono text-slate-400 text-[11px]">${timeFormatted}</td>
                    `;
                    auditTbody.appendChild(tr);
                });
            } else {
                auditTbody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-slate-400">No audit events recorded yet.</td></tr>`;
            }
        }

        runSimulinkSimulation();
    } catch (e) {
        console.error("Admin dashboard error", e);
    }
}

async function adminApproveDoctor(docId) {
    try {
        const res = await fetch(`${API_BASE}/admin/doctor/approve/${docId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to approve doctor.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function adminBlacklistDoctor(docId) {
    if (!confirm("Are you sure you want to blacklist this doctor? Telemedicine review access will be immediately revoked.")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/doctor/blacklist/${docId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "info");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to blacklist doctor.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function adminRemoveDoctor(docId) {
    if (!confirm("Are you sure you want to permanently remove this doctor from the district network? This action cannot be undone.")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/doctor/remove/${docId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to remove doctor.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function adminBlacklistPatient(patId) {
    if (!confirm("Are you sure you want to blacklist this patient account?")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/patient/blacklist/${patId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "info");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to blacklist patient.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function adminActivatePatient(patId) {
    try {
        const res = await fetch(`${API_BASE}/admin/patient/activate/${patId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to restore patient.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function adminRemovePatient(patId) {
    if (!confirm("Are you sure you want to permanently remove this patient and all associated screening data?")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/patient/remove/${patId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to remove patient.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    }
}

async function toggleDoctorActiveStatus(doctorId) {
    try {
        const res = await fetch(`${API_BASE}/admin/doctor/toggle-status/${doctorId}`, { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            loadAdminDashboard();
        }
    } catch (err) {
        showToast("Error updating doctor status: " + err.message, "error");
    }
}

function openAdminAddDoctorModal() {
    document.getElementById("modalAdminAddDoctor").classList.remove("hidden");
}

function closeAdminAddDoctorModal() {
    document.getElementById("modalAdminAddDoctor").classList.add("hidden");
}

async function handleAdminCreateDoctor(e) {
    e.preventDefault();
    const payload = {
        full_name: document.getElementById("admDocFullName").value.trim(),
        username: document.getElementById("admDocUsername").value.trim(),
        email: document.getElementById("admDocEmail").value.trim(),
        license_number: document.getElementById("admDocLicense").value.trim(),
        specialization: document.getElementById("admDocSpec").value.trim(),
        hospital_name: document.getElementById("admDocHospital").value.trim()
    };

    try {
        const res = await fetch(`${API_BASE}/admin/doctor/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
            showToast(data.message, "success");
            closeAdminAddDoctorModal();
            loadAdminDashboard();
        } else {
            showToast(data.error || "Failed to register doctor.", "error");
        }
    } catch (err) {
        showToast("Error: " + err.message, "error");
    }
}

async function runSimulinkSimulation() {
    const annualPatients = parseInt(document.getElementById("simAnnualPatients").value);
    const numPhcs = parseInt(document.getElementById("simPhcCount").value);
    const bandwidth = parseFloat(document.getElementById("simBandwidth").value);
    const filterRate = parseFloat(document.getElementById("simFilterRate").value);

    try {
        const res = await fetch(`${API_BASE}/simulink/simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                annual_patients: annualPatients,
                num_phcs: numPhcs,
                bandwidth_mbps: bandwidth,
                ai_edge_filter_rate: filterRate,
                doctor_review_time_sec: 20
            })
        });

        const data = await res.json();
        const d = data.data;

        document.getElementById("simHoursSaved").innerText = `${d.doctor_capacity_optimization.doctor_hours_saved_daily} Hours / Day`;
        document.getElementById("simWorkloadPct").innerText = `${d.doctor_capacity_optimization.workload_reduction_percentage}% Workload Reduction`;
        document.getElementById("simDoctorsNeeded").innerText = `${d.doctor_capacity_optimization.ophthalmologists_needed_with_ai} Doctor (vs ${d.doctor_capacity_optimization.ophthalmologists_needed_without_ai} without AI)`;
        document.getElementById("simUploadLatency").innerText = `${d.district_metrics.upload_time_per_case_seconds} Sec / Case`;
    } catch (e) {
        console.error("Simulation error", e);
    }
}

// -----------------------------------------------------------------------------
// 10. Helpers & PDF Download
// -----------------------------------------------------------------------------
async function fetchDoctors() {
    try {
        const res = await fetch(`${API_BASE}/auth/doctors`);
        const data = await res.json();
        if (data.doctors && data.doctors.length > 0) {
            const doc = data.doctors[0];
            const nameEl = document.getElementById("patientAssignedDoctorName");
            if (nameEl) nameEl.innerText = doc.full_name;
        }
    } catch (e) {}
}

function downloadPDFReport() {
    if (!activeSessionId) {
        alert("No active screening report selected.");
        return;
    }
    window.open(`${API_BASE}/report/${activeSessionId}/pdf`, "_blank");
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    const colors = {
        success: "bg-emerald-600 text-white",
        error: "bg-rose-600 text-white",
        info: "bg-indigo-900 text-white"
    };
    toast.className = `${colors[type] || colors.info} px-4 py-2.5 rounded-2xl shadow-xl text-xs font-semibold flex items-center space-x-2 transition-all transform duration-300`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
