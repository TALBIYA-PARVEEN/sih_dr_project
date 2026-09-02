// NetraAI Tele-Ophthalmology Fullstack Frontend Logic
// Set your live Render URL here after deploying:
const LIVE_BACKEND_URL = "https://sih-dr-project.onrender.com";
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port === "5000")
    ? (window.location.port === "5000" ? "/api" : "http://127.0.0.1:5000/api")
    : `${LIVE_BACKEND_URL}/api`;

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
    if (pageId === "login") setTimeout(initOfficialGoogleSignIn, 150);
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

let activeGoogleClientId = localStorage.getItem("netra_google_client_id") || "387784977439-ql7h183e12mgdvbfpcd2061d411p269c.apps.googleusercontent.com";

async function fetchGoogleClientId() {
    if (activeGoogleClientId) return activeGoogleClientId;
    try {
        const res = await fetch(`${API_BASE}/auth/google/client-id`);
        const data = await res.json();
        if (data.configured && data.client_id) {
            activeGoogleClientId = data.client_id;
            return activeGoogleClientId;
        }
    } catch (e) {
        console.log("[GOOGLE-FETCH-NOTE]", e);
    }
    return activeGoogleClientId || "387784977439-ql7h183e12mgdvbfpcd2061d411p269c.apps.googleusercontent.com";
}

async function initOfficialGoogleSignIn() {
    const btnContainer = document.getElementById("googleSignInButton");
    if (!btnContainer) return;

    const clientId = await fetchGoogleClientId();

    if (clientId && window.google && google.accounts && google.accounts.id) {
        try {
            google.accounts.id.initialize({
                client_id: clientId,
                callback: handleGoogleCredentialResponse,
                auto_select: false,
                context: "signin"
            });
            btnContainer.innerHTML = "";
            google.accounts.id.renderButton(btnContainer, {
                type: "standard",
                theme: "outline",
                size: "large",
                text: "signin_with",
                shape: "rectangular",
                logo_alignment: "left",
                width: 320
            });
            return;
        } catch (e) {
            console.log("[GOOGLE-ID-INIT-NOTE]", e);
        }
    }

    btnContainer.innerHTML = `
        <button type="button" onclick="triggerGoogleSignIn()" class="w-full py-2.5 px-4 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-semibold rounded-xl text-xs shadow-xs transition flex items-center justify-center space-x-2.5">
            <svg class="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <span>Sign in with Google</span>
        </button>
    `;
}

function triggerGoogleSignIn() {
    if (window.google && google.accounts && google.accounts.id) {
        google.accounts.id.prompt();
    }
}

async function handleGoogleCredentialResponse(response) {
    try {
        showToast("Authenticating with Google...", "info");
        const res = await fetch(`${API_BASE}/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ credential: response.credential, role: "patient" })
        });
        const data = await res.json();
        if (data.status === "success") {
            currentUser = data.user;
            authToken = data.token;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            localStorage.setItem("netra_token", authToken);
            if (typeof updateHeaderAuthUI === "function") updateHeaderAuthUI();
            showToast("Google Sign-In successful! Welcome " + (currentUser.full_name || currentUser.username), "success");
            if (currentUser.role === "doctor") navigateTo("doctor");
            else if (currentUser.role === "admin") navigateTo("admin");
            else navigateTo("patient");
        } else {
            showToast(data.error || "Google authentication failed.", "error");
        }
    } catch (err) {
        showToast("Google Sign-In connection error: " + err.message, "error");
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

function getFormVal(id, fallback = "") {
    const el = document.getElementById(id);
    return el ? el.value.trim() : fallback;
}

function updateHeaderAuthUI() {
    const currentPage = (window.location.hash || "#home").replace("#", "") || "home";
    if (typeof updateNavbarForPage === "function") {
        updateNavbarForPage(currentPage);
    }
}

async function handleRegister(e) {
    if (e && e.preventDefault) e.preventDefault();
    const btn = (e && e.target && e.target.querySelector) ? e.target.querySelector('button[type="submit"]') : document.querySelector('#formRegister button[type="submit"]');
    const originalBtnHtml = btn ? btn.innerHTML : "Register & Send Email OTP";

    const payload = {
        full_name: getFormVal("regFullName", "Patient User"),
        username: getFormVal("regUsername", "user_" + Math.floor(Math.random()*10000)),
        age: parseInt(getFormVal("regAge", "45")) || 45,
        gender: getFormVal("regGender", "Female"),
        email: getFormVal("regEmail", ""),
        password: getFormVal("regPassword", ""),
        phone: getFormVal("regPhone", "+91 9876543210"),
        role: (typeof regRole !== "undefined" && regRole) ? regRole : "patient",
        diabetes_type: getFormVal("regDiabetesType", "Type 2"),
        diabetes_duration_years: parseInt(getFormVal("regDiabetesDuration", "5")) || 5,
        specialization: getFormVal("regSpecialization", ""),
        license_number: getFormVal("regLicense", ""),
        hospital_name: getFormVal("regHospital", "")
    };

    if (!payload.email || !payload.email.includes("@")) {
        showToast("Please enter a valid email address.", "warning");
        return;
    }

    if (!payload.password || payload.password.length < 6) {
        showToast("Password must be at least 6 characters.", "warning");
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Registering & Sending Code...`;
    }

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

            // Open OTP modal only on SUCCESS
            const modal = document.getElementById("modalOtp");
            if (modal) modal.classList.remove("hidden");

            const subtextEl = document.getElementById("otpModalSubtext");
            if (subtextEl) {
                subtextEl.innerHTML = `We sent a 6-digit verification code to <b>${payload.email}</b>.<br><span class="text-indigo-600 font-bold text-xs block mt-1.5"><i class="fa-solid fa-envelope mr-1"></i> Please check your Email Inbox / Spam and enter the code below:</span>`;
            }
            const otpInp = document.getElementById("otpInputCode");
            if (otpInp) {
                otpInp.value = "";
                otpInp.placeholder = "Enter 6-digit code from email";
                otpInp.focus();
            }
            showToast(data.message || `Verification code sent to ${payload.email}`, "success");
        } else {
            // Close OTP modal if by any chance it was open
            const modal = document.getElementById("modalOtp");
            if (modal) modal.classList.add("hidden");
            showToast(data.error || "Registration failed.", "error");
        }
    } catch (err) {
        const modal = document.getElementById("modalOtp");
        if (modal) modal.classList.add("hidden");
        showToast("Server connection error: " + err.message, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalBtnHtml;
        }
    }
}

async function handleVerifyOtp() {
    const code = document.getElementById("otpInputCode").value.trim();
    if (!code || code.length < 6) {
        showToast("Please enter the 6-digit code received in your email.", "warning");
        return;
    }

    const btn = document.querySelector("#modalOtp button.bg-emerald-600");
    const originalBtnHtml = btn ? btn.innerHTML : "Verify & Activate";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Verifying...`;
    }

    try {
        const targetEmail = tempRegisterEmail || 
            (currentUser ? currentUser.email : "") || 
            (document.getElementById("regEmail") ? document.getElementById("regEmail").value.trim() : "") ||
            (document.getElementById("resetEmailInput") ? document.getElementById("resetEmailInput").value.trim() : "");

        if (!targetEmail) {
            showToast("Email address missing. Please enter your email in the registration form.", "error");
            return;
        }

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
            updateHeaderAuthUI();

            if (currentUser && currentUser.role === "doctor") {
                const approval = currentUser.approval_status || currentUser.status;
                if (approval === "pending_approval") {
                    showToast("Email verified! Your doctor registration has been submitted to Master Admin for approval.", "info");
                } else {
                    showToast("Email verified! Welcome Dr. " + (currentUser.full_name || currentUser.username) + "!", "success");
                }
            } else if (currentUser && currentUser.role === "admin") {
                showToast("Email verified! Welcome Admin.", "success");
            } else {
                showToast("Email verified successfully! Welcome to NetraAI, " + (currentUser.full_name || currentUser.username) + "!", "success");
            }
            navigateTo("home");
        } else {
            showToast(data.error || "Invalid verification code. Please check your email.", "error");
        }
    } catch (err) {
        showToast("Verification error: " + err.message, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalBtnHtml;
        }
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
            const subtextEl = document.getElementById("otpModalSubtext");
            if (subtextEl) {
                subtextEl.innerHTML = `We sent a new 6-digit verification code to <b>${targetEmail}</b>.<br><span class="text-indigo-600 font-bold text-xs block mt-1.5"><i class="fa-solid fa-envelope mr-1"></i> Check your Inbox or Spam folder.</span>`;
            }
            const otpInp = document.getElementById("otpInputCode");
            if (otpInp) {
                otpInp.value = "";
                otpInp.placeholder = "Enter 6-digit code from email";
                otpInp.focus();
            }
            showToast(`New verification code sent to ${targetEmail}!`, "success");
        } else {
            showToast(data.error || "Failed to resend code.", "error");
        }
    } catch (e) {
        showToast("Network error: " + e.message, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-rotate-right mr-1"></i> Resend Code`;
        }
    }
}

function closeOtpModal() {
    document.getElementById("modalOtp").classList.add("hidden");
}

function openResetPasswordModal(prefillEmail = "") {
    const modal = document.getElementById("modalResetPassword");
    if (!modal) return;
    modal.classList.remove("hidden");
    const emailInput = document.getElementById("resetEmailInput");
    if (emailInput) {
        if (prefillEmail) emailInput.value = prefillEmail;
        else if (currentUser && currentUser.email) emailInput.value = currentUser.email;
        else {
            const loginUsernameVal = document.getElementById("loginUsername") ? document.getElementById("loginUsername").value.trim() : "";
            if (loginUsernameVal.includes("@")) emailInput.value = loginUsernameVal;
        }
        emailInput.focus();
    }
    const otpInput = document.getElementById("resetOtpInput");
    if (otpInput) otpInput.value = "";
    const newPw = document.getElementById("resetNewPassword");
    if (newPw) newPw.value = "";
    const confPw = document.getElementById("resetConfirmPassword");
    if (confPw) confPw.value = "";
}

function closeResetPasswordModal() {
    const modal = document.getElementById("modalResetPassword");
    if (modal) modal.classList.add("hidden");
}

async function sendResetPasswordOtp() {
    const email = document.getElementById("resetEmailInput").value.trim().toLowerCase();
    if (!email || !email.includes("@")) {
        showToast("Please enter a valid registered email address.", "warning");
        return;
    }
    const btn = document.getElementById("btnSendResetOtp");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Sending...`;
    }
    try {
        const res = await fetch(`${API_BASE}/auth/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`6-digit verification code sent to ${email}. Please check your Inbox / Spam folder.`, "success");
            const otpInput = document.getElementById("resetOtpInput");
            if (otpInput) {
                otpInput.value = "";
                otpInput.focus();
            }
        } else {
            showToast(data.error || "Failed to send verification code.", "error");
        }
    } catch (err) {
        showToast("Network error: " + err.message, "error");
    } finally {
        if (btn) {
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = `<span>Send OTP</span>`;
            }, 4000);
        }
    }
}

async function handleResetPasswordSubmit(e) {
    e.preventDefault();
    const email = document.getElementById("resetEmailInput").value.trim().toLowerCase();
    const otp = document.getElementById("resetOtpInput").value.trim();
    const newPassword = document.getElementById("resetNewPassword").value.trim();
    const confirmPassword = document.getElementById("resetConfirmPassword").value.trim();

    if (!email) {
        showToast("Please enter your registered email address.", "warning");
        return;
    }
    if (!otp || otp.length < 6) {
        showToast("Please enter the 6-digit OTP received in your email.", "warning");
        return;
    }
    if (!newPassword || newPassword.length < 6) {
        showToast("New password must be at least 6 characters long.", "warning");
        return;
    }
    if (newPassword !== confirmPassword) {
        showToast("Passwords do not match. Please re-enter carefully.", "error");
        return;
    }

    const btn = document.getElementById("btnSubmitResetPassword");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Updating Password...`;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/reset-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, otp, new_password: newPassword })
        });
        const data = await res.json();
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-lock-open mr-1"></i><span>Update Password & Log In</span>`;
        }

        if (data.status === "success") {
            closeResetPasswordModal();
            showToast(data.message || "Password updated successfully!", "success");

            if (data.user && data.token) {
                currentUser = data.user;
                authToken = data.token;
                localStorage.setItem("netra_user", JSON.stringify(currentUser));
                localStorage.setItem("netra_token", authToken);

                if (currentUser.role === "patient") navigateTo("patient");
                else if (currentUser.role === "doctor") navigateTo("doctor");
                else if (currentUser.role === "admin") navigateTo("admin");
            } else {
                navigateTo("login");
            }
        } else {
            showToast(data.error || "Password update failed. Please verify your OTP.", "error");
        }
    } catch (err) {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-lock-open mr-1"></i><span>Update Password & Log In</span>`;
        }
        showToast("Server connection error: " + err.message, "error");
    }
}

function openChangePasswordModal() {
    if (currentUser && currentUser.email) {
        openResetPasswordModal(currentUser.email);
    } else {
        openResetPasswordModal();
    }
}

function showForgotPasswordModal() {
    openResetPasswordModal();
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

            let statusBadge = "";
            if (docStatus === "Pending Review" || docStatus === "Pending Clinical Review") {
                statusBadge = `<span class="px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full text-[10px] font-bold inline-flex items-center"><i class="fa-solid fa-clock mr-1"></i> Awaiting Doctor Review</span>`;
            } else if (docStatus === "Confirmed" || docStatus === "Clinically Validated") {
                statusBadge = `<span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold inline-flex items-center"><i class="fa-solid fa-circle-check mr-1"></i> Clinically Validated</span>`;
            } else if (docStatus === "Refer to Specialist" || docStatus === "Requires Hospital Referral") {
                statusBadge = `<span class="px-2.5 py-1 bg-rose-100 text-rose-800 rounded-full text-[10px] font-bold inline-flex items-center"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Specialist Referral</span>`;
            } else {
                statusBadge = `<span class="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full text-[10px] font-bold">${docStatus}</span>`;
            }

            tr.innerHTML = `
                <td class="p-3 font-mono text-slate-500">${dateStr}</td>
                <td class="p-3 font-semibold text-slate-800">${sev}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded-full font-bold ${qual === 'GOOD' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">${qual}</span></td>
                <td class="p-3 text-slate-600">${docName}</td>
                <td class="p-3">${statusBadge}</td>
                <td class="p-3 flex items-center space-x-2">
                    <button onclick="restoreLastSession('${scanId}')" class="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold transition">View Scan</button>
                    <a href="${pdfUrl}" target="_blank" class="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold transition">PDF</a>
                </td>
            `;
            tbody.appendChild(tr);
        });
        if (history.length > 0) {
            const container = document.getElementById("patientResultContainer");
            if (container && container.classList.contains("hidden")) {
                const latestId = history[0].screening_id || history[0].id;
                restoreLastSession(latestId);
            }
        }
    } catch (e) {
        console.error("History load error", e);
    }
}

// -----------------------------------------------------------------------------
// 6. Patient Image Upload & Dual-AI Diagnostic Pipeline (Persists on Refresh)
// -----------------------------------------------------------------------------
let selectedDoctorFile = null;

function setupUploadHandlers() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    if (dropZone && fileInput) {
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

    const docDropZone = document.getElementById("docDropZone");
    const docFileInput = document.getElementById("docFileInput");
    if (docDropZone && docFileInput) {
        docDropZone.addEventListener("click", () => docFileInput.click());
        docFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleDoctorFileSelect(e.target.files[0]);
        });
        docDropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            docDropZone.classList.add("border-emerald-500", "bg-emerald-50/50");
        });
        docDropZone.addEventListener("dragleave", () => {
            docDropZone.classList.remove("border-emerald-500", "bg-emerald-50/50");
        });
        docDropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            docDropZone.classList.remove("border-emerald-500", "bg-emerald-50/50");
            if (e.dataTransfer.files.length > 0) handleDoctorFileSelect(e.dataTransfer.files[0]);
        });
    }
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

function handleDoctorFileSelect(file) {
    selectedDoctorFile = file;
    const nameEl = document.getElementById("docFileNamePreview");
    if (nameEl) nameEl.innerText = file.name;
    const reader = new FileReader();
    reader.onload = (e) => {
        const preview = document.getElementById("docImgPreview");
        if (preview) preview.src = e.target.result;
        const container = document.getElementById("docPreviewContainer");
        if (container) container.classList.remove("hidden");
    };
    reader.readAsDataURL(file);
}

// -----------------------------------------------------------------------------
// Live Retinal Camera Capture & Hardware Device Permissions
// -----------------------------------------------------------------------------
let cameraStream = null;
let currentCameraFacingMode = "environment";
let activeCameraContext = "patient";
let capturedCameraBlob = null;

async function openCameraModal(context = "patient") {
    activeCameraContext = context;
    const modal = document.getElementById("modalCameraCapture");
    if (!modal) return;
    modal.classList.remove("hidden");

    const titleEl = document.getElementById("cameraModalTitle");
    if (titleEl) {
        titleEl.innerText = (context === "doctor") 
            ? "Doctor Station: Live Retinal Camera Capture" 
            : "Patient Screening: Live Retinal Camera Capture";
    }

    retakeCameraPhoto();
    await startCameraStream();
}

async function startCameraStream() {
    const errorBox = document.getElementById("cameraErrorBox");
    const video = document.getElementById("cameraVideo");
    if (errorBox) errorBox.classList.add("hidden");

    stopCameraStream();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showCameraError("Your browser or device does not support direct camera capture. Please use file upload instead.");
        return;
    }

    const constraints = {
        video: {
            facingMode: currentCameraFacingMode,
            width: { ideal: 1920 },
            height: { ideal: 1080 }
        },
        audio: false
    };

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        if (video) {
            video.srcObject = cameraStream;
            video.play();
        }
    } catch (err) {
        console.warn("Camera constraint error with facingMode, falling back to default camera:", err);
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            if (video) {
                video.srcObject = cameraStream;
                video.play();
            }
        } catch (fallbackErr) {
            console.error("Camera access denied or unavailable:", fallbackErr);
            showCameraError("Camera permission was denied or no camera device was detected. Please grant permission in browser settings.");
        }
    }
}

function showCameraError(msg) {
    const errorBox = document.getElementById("cameraErrorBox");
    const errorMsg = document.getElementById("cameraErrorMsg");
    if (errorMsg) errorMsg.innerText = msg;
    if (errorBox) errorBox.classList.remove("hidden");
    showToast(msg, "warning");
}

function switchCameraFacingMode() {
    currentCameraFacingMode = (currentCameraFacingMode === "environment") ? "user" : "environment";
    startCameraStream();
    showToast(`Switched camera to ${currentCameraFacingMode === "environment" ? "Rear / Fundus Lens" : "Front / User"} mode`, "info");
}

function captureCameraSnapshot() {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    if (!video || !canvas) return;

    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, width, height);

    canvas.toBlob((blob) => {
        if (!blob) {
            showToast("Failed to process camera frame. Please try again.", "error");
            return;
        }
        capturedCameraBlob = blob;
        const snapshotImg = document.getElementById("cameraSnapshotImg");
        if (snapshotImg) {
            snapshotImg.src = URL.createObjectURL(blob);
        }

        const reticle = document.getElementById("cameraReticleOverlay");
        const snapCont = document.getElementById("cameraSnapshotContainer");
        const liveCtrls = document.getElementById("cameraLiveControls");
        const revCtrls = document.getElementById("cameraReviewControls");

        if (reticle) reticle.classList.add("hidden");
        if (snapCont) snapCont.classList.remove("hidden");
        if (liveCtrls) liveCtrls.classList.add("hidden");
        if (revCtrls) revCtrls.classList.remove("hidden");
    }, "image/png", 0.95);
}

function retakeCameraPhoto() {
    capturedCameraBlob = null;
    const reticle = document.getElementById("cameraReticleOverlay");
    const snapCont = document.getElementById("cameraSnapshotContainer");
    const liveCtrls = document.getElementById("cameraLiveControls");
    const revCtrls = document.getElementById("cameraReviewControls");

    if (reticle) reticle.classList.remove("hidden");
    if (snapCont) snapCont.classList.add("hidden");
    if (liveCtrls) liveCtrls.classList.remove("hidden");
    if (revCtrls) revCtrls.classList.add("hidden");
}

function confirmCameraSnapshot() {
    if (!capturedCameraBlob) {
        showToast("No camera photo captured yet.", "warning");
        return;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `camera_retina_scan_${timestamp}.png`;
    const capturedFile = new File([capturedCameraBlob], filename, { type: "image/png" });

    if (activeCameraContext === "doctor") {
        selectedDoctorFile = capturedFile;
        const preview = document.getElementById("docImgPreview");
        const nameEl = document.getElementById("docFileNamePreview");
        const container = document.getElementById("docPreviewContainer");

        if (preview) preview.src = URL.createObjectURL(capturedCameraBlob);
        if (nameEl) nameEl.innerHTML = `<i class="fa-solid fa-camera mr-1 text-emerald-600"></i> ${filename} (${(capturedCameraBlob.size / 1024).toFixed(1)} KB)`;
        if (container) container.classList.remove("hidden");

        showToast("Retinal photo captured via camera & ready for screening!", "success");
    } else {
        selectedFile = capturedFile;
        const preview = document.getElementById("imgPreview");
        const nameEl = document.getElementById("fileNamePreview");
        const container = document.getElementById("previewContainer");

        if (preview) preview.src = URL.createObjectURL(capturedCameraBlob);
        if (nameEl) nameEl.innerHTML = `<i class="fa-solid fa-camera mr-1 text-indigo-600"></i> ${filename} (${(capturedCameraBlob.size / 1024).toFixed(1)} KB)`;
        if (container) container.classList.remove("hidden");

        showToast("Retinal photo captured via camera & ready for screening!", "success");
    }

    closeCameraModal();
}

function stopCameraStream() {
    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop());
        cameraStream = null;
    }
    const video = document.getElementById("cameraVideo");
    if (video) video.srcObject = null;
}

function closeCameraModal() {
    stopCameraStream();
    const modal = document.getElementById("modalCameraCapture");
    if (modal) modal.classList.add("hidden");
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

        if (result.status === "rejected" || result.status === "warning" || result.is_gradable === false || !res.ok) {
            document.getElementById("rejectionCard").classList.remove("hidden");
            document.getElementById("patientResultContainer").classList.add("hidden");
            const reason = result.message || result.error || (result.quality_assessment ? result.quality_assessment.rejection_reason : "Image is not suitable for clinical grading. Please recapture an authentic eye fundus photograph.");
            document.getElementById("rejectionReasonText").innerHTML = `<b>Diagnostic Assessment:</b> ${reason}`;
            showToast("Scan Rejected: " + (result.message || "Please upload an authentic retinal photo."), "error");
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

    const rev = data.clinician_review || {};
    const statusText = rev.status || data.review_status || "Pending Review";
    const statusEl = document.getElementById("patientDocStatus");
    if (statusEl) {
        statusEl.innerText = statusText;
        if (statusText === "Confirmed" || statusText === "Clinically Validated") {
            statusEl.className = "font-bold text-emerald-600";
        } else if (statusText === "Refer to Specialist" || statusText === "Requires Hospital Referral") {
            statusEl.className = "font-bold text-rose-600";
        } else {
            statusEl.className = "font-bold text-amber-600";
        }
    }
    const notesEl = document.getElementById("patientDocNotes");
    if (notesEl) {
        notesEl.innerText = rev.notes || (statusText === "Pending Review" ? `Awaiting examining ophthalmologist sign-off (${data.assigned_doctor_name || 'Assigned Specialist'}).` : "Clinical evaluation completed.");
    }
    
    const assignedDocNameEl = document.getElementById("patientAssignedDoctorName");
    if (assignedDocNameEl && data.assigned_doctor_name) {
        assignedDocNameEl.innerText = data.assigned_doctor_name;
    }
}

// -----------------------------------------------------------------------------
// 7. Doctor Workstation & Clinical Screening
// -----------------------------------------------------------------------------
function switchDoctorTab(tab) {
    const tabWorkstation = document.getElementById("tabDoctorWorkstation");
    const tabScreening = document.getElementById("tabDoctorScreening");
    const tabChat = document.getElementById("tabDoctorChat");
    const contentWorkstation = document.getElementById("doctorTabWorkstationContent");
    const contentScreening = document.getElementById("doctorTabScreeningContent");
    const contentChat = document.getElementById("doctorTabChatContent");

    const inactiveClass = "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition flex items-center space-x-1";
    const activeClass = "px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold shadow-sm transition flex items-center space-x-1";

    if (tabWorkstation) tabWorkstation.className = (tab === "workstation" ? activeClass : inactiveClass);
    if (tabScreening) tabScreening.className = (tab === "screening" ? activeClass : inactiveClass);
    if (tabChat) tabChat.className = (tab === "chat" ? activeClass : inactiveClass);

    if (contentWorkstation) contentWorkstation.classList.toggle("hidden", tab !== "workstation");
    if (contentScreening) contentScreening.classList.toggle("hidden", tab !== "screening");
    if (contentChat) contentChat.classList.toggle("hidden", tab !== "chat");

    if (tab === "chat") loadDoctorChat();
    if (tab === "workstation") loadDoctorQueue();
}

async function handleDoctorScreeningSubmit(e) {
    e.preventDefault();
    if (!selectedDoctorFile) {
        showToast("Please select or drop a retinal fundus image.", "warning");
        return;
    }

    const patientName = document.getElementById("docScanPatientName").value.trim();
    const patientEmail = document.getElementById("docScanPatientEmail").value.trim();
    const patientPhone = document.getElementById("docScanPatientPhone").value.trim();
    const patientAge = document.getElementById("docScanPatientAge").value;
    const patientGender = document.getElementById("docScanPatientGender").value;
    const diabetesType = document.getElementById("docScanDiabetesType").value;
    const diabetesDuration = document.getElementById("docScanDiabetesDuration").value;
    const doctorNotes = document.getElementById("docScanNotes").value.trim();

    const submitBtn = document.getElementById("btnDocScreenSubmit");
    const origBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Analyzing Fundus & Generating Report...`;

    const formData = new FormData();
    formData.append("file", selectedDoctorFile);
    formData.append("patient_name", patientName);
    formData.append("patient_email", patientEmail);
    formData.append("patient_phone", patientPhone);
    formData.append("patient_age", patientAge);
    formData.append("patient_gender", patientGender);
    formData.append("diabetes_type", diabetesType);
    formData.append("diabetes_duration_years", diabetesDuration);
    formData.append("doctor_notes", doctorNotes || "Retinal fundus analysis confirmed by clinician.");
    formData.append("clinical_status", "Confirmed");
    if (currentUser) {
        formData.append("doctor_user_id", currentUser.id);
    }

    try {
        const res = await fetch(`${API_BASE}/doctor/screen`, {
            method: "POST",
            body: formData
        });
        const result = await res.json();
        submitBtn.disabled = false;
        submitBtn.innerHTML = origBtnText;

        if (result.status === "rejected" || result.is_gradable === false || !res.ok) {
            const reason = result.message || result.error || (result.quality_assessment ? result.quality_assessment.rejection_reason : "The uploaded image is not a valid retina scan or is ungradable.");
            showToast("Quality Assessment Failed: " + reason, "error");
            alert("Scan Rejected (Non-Retinal or Ungradable Image)\n\n" + reason + "\n\nAction Required: Please recapture and upload an authentic retinal fundus photograph.");
            return;
        }

        if (result.status === "success" || result.status === "warning") {
            const data = result.data;
            const pred = data.prediction || {};
            const iqa = data.quality_assessment || {};

            document.getElementById("docScreeningPlaceholder").classList.add("hidden");
            document.getElementById("docScreeningResultsCard").classList.remove("hidden");

            document.getElementById("docResPatientHeader").innerText = `Diagnosis for ${patientName} (${patientAge}y, ${patientGender})`;
            document.getElementById("docResMeta").innerText = `Assigned to Dr. ${currentUser ? (currentUser.full_name || currentUser.username) : 'Doctor'} • Added to your Review Queue`;

            document.getElementById("docResSeverityName").innerText = pred.severity_name || "Diagnostic Complete";
            document.getElementById("docResConfidence").innerText = `Confidence: ${(pred.confidence ? (pred.confidence * 100).toFixed(1) : '95.0')}%`;

            document.getElementById("docResQualityLabel").innerText = iqa.quality_label || "Gradable";
            document.getElementById("docResQualityScore").innerText = `IQA Score: ${iqa.overall_score || 92}/100`;

            document.getElementById("docResOrigImg").src = `${API_BASE}/files/${result.session_id}/original`;
            document.getElementById("docResVesselImg").src = `${API_BASE}/files/${result.session_id}/vessels`;
            document.getElementById("docResLesionImg").src = `${API_BASE}/files/${result.session_id}/lesions`;
            document.getElementById("docResGradcamImg").src = `${API_BASE}/files/${result.session_id}/gradcam`;

            document.getElementById("docResDownloadPdfBtn").href = `${API_BASE}/report/${result.session_id}/pdf`;
            document.getElementById("docResDoctorNotes").innerText = doctorNotes || "Pending doctor clinical validation in Review Queue.";

            // Credentials & email banner
            const notifText = document.getElementById("docPatientEmailNotificationText");
            const pwBadge = document.getElementById("docPatientTempPwBadge");

            if (result.is_new_patient && result.temp_password) {
                notifText.innerHTML = `New patient account created for <b>${patientEmail}</b>.<br><span class="text-xs text-slate-600">Patient can log in at any time with Email: <b>${patientEmail}</b> & Passcode: <code class="bg-indigo-100 text-indigo-900 px-2 py-0.5 rounded font-mono font-bold">${result.temp_password}</code></span>`;
                pwBadge.innerText = `Login Passcode: ${result.temp_password}`;
                pwBadge.classList.remove("hidden");
            } else {
                notifText.innerHTML = `Diagnostic scan attached to existing patient dashboard for <b>${patientEmail}</b>. (Existing credentials preserved).`;
                pwBadge.classList.add("hidden");
            }

            showToast("Screening analyzed & patient added to your Review Queue. Please complete sign-off in the queue.", "success");
            currentDoctorSession = data;
            loadDoctorQueue();
        } else {
            showToast(result.error || "Screening error occurred.", "error");
        }
    } catch (err) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origBtnText;
        showToast("Server connection error: " + err.message, "error");
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
            list.innerHTML = `<div class="text-xs text-slate-400 text-center py-6">All assigned patient scans have been clinically validated! No pending scans in queue.</div>`;
            document.getElementById("doctorStationEmpty").classList.remove("hidden");
            document.getElementById("doctorStationContent").classList.add("hidden");
            currentDoctorSession = null;
            return;
        }

        doctorQueue.forEach((s) => {
            const isRef = s.prediction && s.prediction.is_referable;
            const reviewStatus = (s.clinician_review && s.clinician_review.status) || s.review_status || "Pending Review";
            const dateStr = s.created_at ? new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Just now";
            const item = document.createElement("div");
            item.className = "p-3 rounded-2xl border border-slate-200 hover:border-emerald-500 cursor-pointer transition bg-white space-y-1 group";
            item.onclick = () => selectDoctorPatient(s);

            item.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="font-bold text-xs text-slate-800 group-hover:text-emerald-700 transition">${s.patient_name || 'Patient Scan'}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold ${isRef ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}">
                        ${s.prediction ? s.prediction.severity_name.split('(')[0] : 'Scanned'}
                    </span>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-400">
                    <span>Age: ${s.patient_age || 'N/A'} • ${s.patient_gender || 'Scan'}</span>
                    <span class="font-semibold text-slate-600">${reviewStatus} (${dateStr})</span>
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
    if (!session) return;
    currentDoctorSession = session;
    activeSessionId = session.id;

    document.getElementById("doctorStationEmpty").classList.add("hidden");
    document.getElementById("doctorStationContent").classList.remove("hidden");

    const patientName = session.patient_name || 'Anonymous Patient';
    const patientAge = session.patient_age || 'N/A';
    const patientGender = session.patient_gender || 'N/A';
    const diabetesInfo = session.diabetes_info || 'Type 2 Diabetes';

    document.getElementById("docPatientName").innerText = `Patient: ${patientName}`;
    document.getElementById("docPatientMeta").innerText = `Age: ${patientAge} • Gender: ${patientGender} • ${diabetesInfo}`;

    const pred = session.prediction || {};
    const aiBadge = document.getElementById("docAIStatusBadge");
    if (aiBadge) {
        aiBadge.innerText = pred.severity_name || "Diagnostic Complete";
        if (pred.is_referable) {
            aiBadge.className = "px-3 py-1 bg-rose-100 text-rose-800 rounded-full text-xs font-bold border border-rose-200";
        } else {
            aiBadge.className = "px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold border border-emerald-200";
        }
    }

    document.getElementById("docScanOrig").src = `${API_BASE}/files/${session.id}/original`;
    document.getElementById("docScanVessels").src = `${API_BASE}/files/${session.id}/vessels`;
    document.getElementById("docScanLesions").src = `${API_BASE}/files/${session.id}/lesions`;
    document.getElementById("docScanGradcam").src = `${API_BASE}/files/${session.id}/gradcam`;

    const rev = session.clinician_review || {};
    const statusSelect = document.getElementById("docSelectStatus");
    if (statusSelect) statusSelect.value = rev.status || session.review_status || "Confirmed";

    const notesInput = document.getElementById("docInputNotes");
    if (notesInput) notesInput.value = rev.notes || "";
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
    try {
        const res = await fetch(`${API_BASE}/messages/patient/${currentUser.id}`);
        const data = await res.json();
        const stream = document.getElementById("patientChatMessagesStream");
        if (!stream) return;
        stream.innerHTML = "";

        if (!data.messages || data.messages.length === 0) {
            stream.innerHTML = `<div class="text-xs text-slate-400 text-center py-10">No messages yet. When your examining doctor reviews your retina scan, their clinical directives & sign-off will appear here automatically.</div>`;
            return;
        }

        data.messages.forEach(m => {
            const isMe = m.sender_id === currentUser.id;
            const timeStr = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
            const bubble = document.createElement("div");
            bubble.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;
            bubble.innerHTML = `
                <div class="max-w-xs p-3 rounded-2xl text-xs ${isMe ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs'} space-y-1">
                    <div class="flex items-center justify-between text-[10px] opacity-75 space-x-2">
                        <span class="font-bold">${m.sender_name || (isMe ? 'You' : 'Doctor')} (${m.sender_role || 'doctor'})</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="leading-relaxed">${m.content}</div>
                </div>
            `;
            stream.appendChild(bubble);
        });
        stream.scrollTop = stream.scrollHeight;
    } catch (e) {
        console.error("loadPatientChat error:", e);
    }
}

async function handlePatientSendMessage(e) {
    e.preventDefault();
    if (!currentUser) return;
    const input = document.getElementById("inputPatientMessage");
    const content = input.value.trim();
    if (!content) return;

    let recipientId = currentUser.assigned_doctor_id;
    if (!recipientId || recipientId === "doc_demo") {
        try {
            const docRes = await fetch(`${API_BASE}/auth/doctors`);
            const docData = await docRes.json();
            if (docData.doctors && docData.doctors.length > 0) {
                recipientId = docData.doctors[0].user_id || docData.doctors[0].id;
            } else {
                recipientId = "doctor";
            }
        } catch (e) {
            recipientId = "doctor";
        }
    }

    try {
        const res = await fetch(`${API_BASE}/messages/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sender_id: currentUser.id,
                recipient_id: recipientId,
                content: content,
                screening_id: activeSessionId || null
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = "";
            loadPatientChat();
        } else {
            showToast(data.error || "Failed to send message.", "error");
        }
    } catch (err) {
        showToast("Error sending message: " + err.message, "error");
    }
}

let doctorChatPatientsList = [];
let activeDoctorChatPatient = null;

function openDoctorChatForCurrentPatient() {
    switchDoctorTab('chat');
    if (currentDoctorSession && currentDoctorSession.patient_user_id) {
        loadDoctorChat(currentDoctorSession.patient_user_id);
    } else {
        loadDoctorChat();
    }
}

async function loadDoctorChat(preselectPatientId = null) {
    if (!currentUser) return;
    const docId = currentUser.id;
    try {
        const res = await fetch(`${API_BASE}/doctor/chat/patients/${docId}`);
        const data = await res.json();
        doctorChatPatientsList = data.patients || [];
        const countEl = document.getElementById("docChatPatientCount");
        if (countEl) countEl.innerText = doctorChatPatientsList.length;

        renderDoctorChatPatients(doctorChatPatientsList);

        if (doctorChatPatientsList.length > 0) {
            let targetPatient = doctorChatPatientsList[0];
            if (preselectPatientId) {
                const found = doctorChatPatientsList.find(p => p.id === preselectPatientId || p.user_id === preselectPatientId);
                if (found) targetPatient = found;
            } else if (currentDoctorSession && currentDoctorSession.patient_user_id) {
                const found = doctorChatPatientsList.find(p => p.id === currentDoctorSession.patient_user_id || p.user_id === currentDoctorSession.patient_user_id);
                if (found) targetPatient = found;
            }
            selectDoctorChatPatient(targetPatient);
        } else {
            const listEl = document.getElementById("docChatPatientList");
            if (listEl) listEl.innerHTML = `<div class="text-xs text-slate-400 text-center py-8">No patients registered in your directory yet.</div>`;
            document.getElementById("docActiveChatPatientName").innerText = "No Patients Available";
            document.getElementById("docActiveChatPatientMeta").innerText = "Patients will appear here when registered or screened.";
            document.getElementById("doctorChatMessagesStream").innerHTML = `<div class="text-xs text-slate-400 text-center py-16">No patient selected.</div>`;
        }
    } catch (e) {
        console.error("loadDoctorChat error:", e);
    }
}

function renderDoctorChatPatients(patients) {
    const listEl = document.getElementById("docChatPatientList");
    if (!listEl) return;
    listEl.innerHTML = "";

    if (!patients || patients.length === 0) {
        listEl.innerHTML = `<div class="text-xs text-slate-400 text-center py-8">No matching patients found.</div>`;
        return;
    }

    patients.forEach(p => {
        const isSelected = activeDoctorChatPatient && (activeDoctorChatPatient.id === p.id || activeDoctorChatPatient.user_id === p.user_id);
        const item = document.createElement("div");
        item.className = `p-3 rounded-2xl border cursor-pointer transition flex items-center justify-between ${
            isSelected 
                ? 'bg-emerald-50 border-emerald-500 shadow-xs' 
                : 'bg-white border-slate-200 hover:border-emerald-300 hover:bg-slate-50'
        }`;
        item.onclick = () => selectDoctorChatPatient(p);

        item.innerHTML = `
            <div class="flex items-center space-x-2.5 overflow-hidden">
                <div class="w-8 h-8 rounded-full ${isSelected ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'} flex items-center justify-center font-bold text-xs flex-shrink-0">
                    ${(p.full_name || 'P')[0].toUpperCase()}
                </div>
                <div class="truncate">
                    <div class="font-bold text-xs text-slate-800 truncate">${p.full_name || 'Patient'}</div>
                    <div class="text-[10px] text-slate-400 truncate">${p.last_message || 'No messages'}</div>
                </div>
            </div>
            <div class="text-right flex-shrink-0 ml-2">
                <span class="text-[9px] text-slate-400 block">${p.age ? p.age + 'y' : ''}</span>
            </div>
        `;
        listEl.appendChild(item);
    });
}

function filterDoctorChatPatients() {
    const query = (document.getElementById("docChatSearchInput").value || "").trim().toLowerCase();
    if (!query) {
        renderDoctorChatPatients(doctorChatPatientsList);
        return;
    }
    const filtered = doctorChatPatientsList.filter(p => 
        (p.full_name && p.full_name.toLowerCase().includes(query)) ||
        (p.email && p.email.toLowerCase().includes(query)) ||
        (p.phone && p.phone.includes(query))
    );
    renderDoctorChatPatients(filtered);
}

function selectDoctorChatPatient(patient) {
    activeDoctorChatPatient = patient;
    renderDoctorChatPatients(doctorChatPatientsList);

    const nameEl = document.getElementById("docActiveChatPatientName");
    const metaEl = document.getElementById("docActiveChatPatientMeta");
    if (nameEl) nameEl.innerText = patient.full_name || 'Patient';
    if (metaEl) metaEl.innerText = `Age: ${patient.age || 'N/A'} • Gender: ${patient.gender || 'N/A'} • ${patient.email || patient.phone || 'In-App Consultation'}`;

    loadDoctorConversationThread(patient.id || patient.user_id);
}

async function loadDoctorConversationThread(patientId) {
    if (!currentUser || !patientId) return;
    try {
        const res = await fetch(`${API_BASE}/messages/thread/${currentUser.id}/${patientId}`);
        const data = await res.json();
        const stream = document.getElementById("doctorChatMessagesStream");
        if (!stream) return;
        stream.innerHTML = "";

        if (!data.messages || data.messages.length === 0) {
            stream.innerHTML = `<div class="text-xs text-slate-400 text-center py-16">No previous messages with <b>${activeDoctorChatPatient ? activeDoctorChatPatient.full_name : 'this patient'}</b>.<br>Type clinical directives or advice below to begin tele-consultation.</div>`;
            return;
        }

        data.messages.forEach(m => {
            const isMe = m.sender_id === currentUser.id;
            const timeStr = m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
            const bubble = document.createElement("div");
            bubble.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;
            bubble.innerHTML = `
                <div class="max-w-sm p-3 rounded-2xl text-xs ${isMe ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs'} space-y-1">
                    <div class="flex items-center justify-between text-[10px] opacity-75 space-x-2">
                        <span class="font-bold">${m.sender_name || (isMe ? 'You (Doctor)' : 'Patient')}</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="leading-relaxed">${m.content}</div>
                </div>
            `;
            stream.appendChild(bubble);
        });
        stream.scrollTop = stream.scrollHeight;
    } catch (e) {
        console.error("loadDoctorConversationThread error:", e);
    }
}

function insertQuickAdvice(text) {
    const input = document.getElementById("inputDoctorMessage");
    if (input) {
        input.value = text;
        input.focus();
    }
}

async function handleDoctorSendMessage(e) {
    e.preventDefault();
    if (!currentUser) return;
    if (!activeDoctorChatPatient) {
        showToast("Please select a patient from the list on the left.", "warning");
        return;
    }
    const input = document.getElementById("inputDoctorMessage");
    const content = input.value.trim();
    if (!content) return;

    const recipientId = activeDoctorChatPatient.id || activeDoctorChatPatient.user_id;
    const btn = document.getElementById("btnDoctorSendMessage");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/messages/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sender_id: currentUser.id,
                recipient_id: recipientId,
                content: content,
                screening_id: activeSessionId || null
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = "";
            loadDoctorConversationThread(recipientId);
            if (activeDoctorChatPatient) {
                activeDoctorChatPatient.last_message = content;
                renderDoctorChatPatients(doctorChatPatientsList);
            }
        } else {
            showToast(data.error || "Failed to send message.", "error");
        }
    } catch (err) {
        showToast("Error sending message: " + err.message, "error");
    } finally {
        if (btn) btn.disabled = false;
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

let lastCreatedDoctorCredentials = null;

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
            showToast("Doctor registered and approved!", "success");
            closeAdminAddDoctorModal();
            loadAdminDashboard();

            // Populate on-screen credentials display modal
            const creds = data.credentials || payload;
            creds.password = creds.password || "Doctor@2026";
            lastCreatedDoctorCredentials = creds;

            const nameEl = document.getElementById("docSuccessName");
            if (nameEl) nameEl.innerText = creds.full_name;
            const uEl = document.getElementById("docSuccessUsername");
            if (uEl) uEl.innerText = creds.username;
            const emEl = document.getElementById("docSuccessEmail");
            if (emEl) emEl.innerText = creds.email;
            const pwEl = document.getElementById("docSuccessPassword");
            if (pwEl) pwEl.innerText = creds.password;
            const licEl = document.getElementById("docSuccessLicense");
            if (licEl) licEl.innerText = creds.license_number;

            const modalSucc = document.getElementById("modalDoctorCreatedSuccess");
            if (modalSucc) modalSucc.classList.remove("hidden");
        } else {
            showToast(data.error || "Failed to register doctor.", "error");
        }
    } catch (err) {
        showToast("Error: " + err.message, "error");
    }
}

function closeDoctorCreatedSuccessModal() {
    const modalSucc = document.getElementById("modalDoctorCreatedSuccess");
    if (modalSucc) modalSucc.classList.add("hidden");
}

function copyDoctorCredentialsToClipboard() {
    if (!lastCreatedDoctorCredentials) return;
    const text = `NetraAI Doctor Portal Credentials:
Name: ${lastCreatedDoctorCredentials.full_name}
Username: ${lastCreatedDoctorCredentials.username}
Email: ${lastCreatedDoctorCredentials.email}
Password: ${lastCreatedDoctorCredentials.password || 'Doctor@2026'}
License: ${lastCreatedDoctorCredentials.license_number}`;

    navigator.clipboard.writeText(text).then(() => {
        showToast("Doctor login credentials copied to clipboard!", "success");
    }).catch(() => {
        showToast("Password: " + (lastCreatedDoctorCredentials.password || "Doctor@2026"), "info");
    });
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
    if (!container) return;
    const toast = document.createElement("div");
    const colors = {
        success: "bg-emerald-600 text-white border border-emerald-500",
        error: "bg-rose-600 text-white border border-rose-500",
        info: "bg-indigo-950 text-white border border-indigo-700"
    };
    toast.className = `${colors[type] || colors.info} px-4 py-2.5 rounded-2xl shadow-2xl text-xs font-semibold flex items-center space-x-2 transition-all transform duration-300 pointer-events-auto`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
