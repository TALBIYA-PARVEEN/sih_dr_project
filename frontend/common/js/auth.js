// NetraAI Authentication, Security & Session Management Module

let currentUser = null;
let authToken = null;
let tempRegisterEmail = null;
let regRole = "patient";

function initAuth() {
    try {
        const storedUser = localStorage.getItem("netra_user");
        const storedToken = localStorage.getItem("netra_token");
        if (storedUser && storedToken) {
            currentUser = JSON.parse(storedUser);
            authToken = storedToken;
        }
    } catch (e) {
        console.error("Auth init error:", e);
    }
    updateHeaderAuthUI();
}

function fillLogin(u, p) {
    const userIn = document.getElementById("loginUsername");
    const passIn = document.getElementById("loginPassword");
    if (userIn) userIn.value = u;
    if (passIn) passIn.value = p;
    if (passIn && !p) passIn.focus();
}

function openLoginModal(role = "patient") {
    navigateTo("login");
}

function openRegisterModal(role = "patient") {
    setRegisterRole(role);
    navigateTo("register");
}

function setRegisterRole(role) {
    regRole = role;
    const tabP = document.getElementById("tabRegPatient");
    const tabD = document.getElementById("tabRegDoctor");
    const docFields = document.getElementById("doctorExtraFields");
    const patFields = document.getElementById("patientExtraFields");

    if (role === "doctor") {
        if (tabD) tabD.className = "py-2 text-xs font-bold rounded-lg bg-white shadow text-emerald-700 transition";
        if (tabP) tabP.className = "py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-indigo-700 transition";
        if (docFields) docFields.classList.remove("hidden");
        if (patFields) patFields.classList.add("hidden");
    } else {
        if (tabP) tabP.className = "py-2 text-xs font-bold rounded-lg bg-white shadow text-indigo-700 transition";
        if (tabD) tabD.className = "py-2 text-xs font-bold rounded-lg text-slate-600 hover:text-indigo-700 transition";
        if (docFields) docFields.classList.add("hidden");
        if (patFields) patFields.classList.remove("hidden");
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const user = document.getElementById("loginUsername").value.trim();
    const pass = document.getElementById("loginPassword").value.trim();

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();

        if (data.status === "success") {
            currentUser = data.user;
            authToken = data.token;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            localStorage.setItem("netra_token", authToken);
            updateHeaderAuthUI();

            showToast("Welcome, " + (currentUser.full_name || currentUser.username) + "!", "success");

            if (currentUser.role === "doctor") {
                navigateTo("doctor");
            } else if (currentUser.role === "admin") {
                navigateTo("admin");
            } else {
                navigateTo("patient");
            }
        } else {
            showToast(data.error || "Login failed. Please check credentials.", "error");
        }
    } catch (err) {
        showToast("Error connecting to server: " + err.message, "error");
    }
}

function getFormVal(id, fallback = "") {
    const el = document.getElementById(id);
    return el ? el.value.trim() : fallback;
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

    // 1. Open the OTP modal IMMEDIATELY (0ms instant response)
    tempRegisterEmail = payload.email;
    const modal = document.getElementById("modalOtp");
    if (modal) modal.classList.remove("hidden");
    const subtextEl = document.getElementById("otpModalSubtext");
    if (subtextEl) {
        subtextEl.innerHTML = `
            <div class="p-3 bg-indigo-50 border border-indigo-200 rounded-2xl text-center">
                <div class="text-xs text-indigo-700 font-bold flex items-center justify-center gap-2">
                    <i class="fa-solid fa-spinner fa-spin"></i> Generating OTP & Sending to <b>${payload.email}</b>...
                </div>
            </div>`;
    }
    const otpInp = document.getElementById("otpInputCode");
    if (otpInp) {
        otpInp.value = "";
        otpInp.focus();
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Processing...`;
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

            const otpCode = data.dev_otp || (data.user ? data.user.otp_code : null);
            let subtext = `We sent a 6-digit verification code to <b>${payload.email}</b>.<br><span class="text-indigo-600 font-bold text-xs block mt-1.5"><i class="fa-solid fa-envelope mr-1"></i> Check your Inbox / Spam folder.</span>`;
            
            if (otpCode) {
                subtext += `<div class="mt-3 p-3 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-xs text-emerald-950 flex items-center justify-between shadow-xs">
                    <div>
                        <span class="font-bold text-[11px] block text-emerald-700"><i class="fa-solid fa-shield-check mr-1"></i> Security Verification OTP:</span>
                        <span class="font-mono text-lg font-black tracking-widest text-emerald-800">${otpCode}</span>
                    </div>
                    <button type="button" onclick="document.getElementById('otpInputCode').value='${otpCode}'; handleVerifyOtp();" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition flex items-center">
                        <i class="fa-solid fa-bolt mr-1"></i> Auto-Fill & Verify
                    </button>
                </div>`;
            }
            if (subtextEl) subtextEl.innerHTML = subtext;
            if (otpInp) {
                otpInp.value = otpCode || "";
                otpInp.placeholder = "Enter 6-digit code";
                otpInp.focus();
            }
            showToast(data.message || `Verification code sent to ${payload.email}`, "success");
        } else {
            showToast(data.error || "Registration failed.", "error");
            if (subtextEl) {
                subtextEl.innerHTML = `<span class="text-rose-600 font-semibold">${data.error || "Registration error occurred."}</span>`;
            }
        }
    } catch (err) {
        showToast("Server connection error: " + err.message, "error");
        if (subtextEl) {
            subtextEl.innerHTML = `<span class="text-rose-600 font-semibold">Could not reach server: ${err.message}</span>`;
        }
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
                    showToast("Email verified! Your doctor registration is submitted to District Master Admin for approval.", "info");
                    navigateTo("landing");
                } else {
                    showToast("Email verified! Welcome Dr. " + currentUser.full_name, "success");
                    navigateTo("doctor");
                }
            } else if (currentUser && currentUser.role === "admin") {
                navigateTo("admin");
            } else {
                showToast("Email verified successfully! Welcome to NetraAI, " + (currentUser.full_name || currentUser.username) + "!", "success");
                navigateTo("patient");
            }
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
            const newOtp = data.dev_otp;
            let subtext = `New 6-digit verification code sent to <b>${targetEmail}</b>.`;
            if (newOtp) {
                subtext += `<div class="mt-3 p-3 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-xs text-emerald-950 flex items-center justify-between shadow-xs">
                    <div>
                        <span class="font-bold text-[11px] block text-emerald-700"><i class="fa-solid fa-shield-check mr-1"></i> New Security OTP:</span>
                        <span class="font-mono text-lg font-black tracking-widest text-emerald-800">${newOtp}</span>
                    </div>
                    <button type="button" onclick="document.getElementById('otpInputCode').value='${newOtp}'; handleVerifyOtp();" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition flex items-center">
                        <i class="fa-solid fa-bolt mr-1"></i> Auto-Fill & Verify
                    </button>
                </div>`;
                document.getElementById("otpInputCode").value = newOtp;
            }
            if (subtextEl) subtextEl.innerHTML = subtext;
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
    const modal = document.getElementById("modalOtp");
    if (modal) modal.classList.add("hidden");
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
                updateHeaderAuthUI();

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

function openEditProfileModal() {
    if (!currentUser) return;
    document.getElementById("modalEditProfile").classList.remove("hidden");

    document.getElementById("editProfileName").value = currentUser.full_name || currentUser.username || "";
    document.getElementById("editProfilePhone").value = currentUser.phone || "";

    const patFields = document.getElementById("editPatientFields");
    const docFields = document.getElementById("editDoctorFields");

    if (currentUser.role === "doctor") {
        document.getElementById("editProfileModalTitle").innerHTML = `<i class="fa-solid fa-user-doctor text-emerald-600 mr-2"></i><span>Edit Doctor Clinical Profile</span>`;
        if (patFields) patFields.classList.add("hidden");
        if (docFields) docFields.classList.remove("hidden");

        document.getElementById("editProfileSpecialization").value = currentUser.specialization || "";
        document.getElementById("editProfileLicense").value = currentUser.license_number || "";
        document.getElementById("editProfileHospital").value = currentUser.hospital_name || "";
    } else {
        document.getElementById("editProfileModalTitle").innerHTML = `<i class="fa-solid fa-user-pen text-indigo-600 mr-2"></i><span>Edit Patient Profile</span>`;
        if (docFields) docFields.classList.add("hidden");
        if (patFields) patFields.classList.remove("hidden");

        document.getElementById("editProfileAge").value = currentUser.age || 50;
        document.getElementById("editProfileGender").value = currentUser.gender || "Female";
        document.getElementById("editProfileDiabetesType").value = currentUser.diabetes_type || "Type 2";
        document.getElementById("editProfileDiabetesDuration").value = currentUser.diabetes_duration_years || 5;
    }
}

function closeEditProfileModal() {
    const modal = document.getElementById("modalEditProfile");
    if (modal) modal.classList.add("hidden");
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
        const res = await fetch(`${API_BASE}/user/profile/${currentUser.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
            currentUser = data.user;
            localStorage.setItem("netra_user", JSON.stringify(currentUser));
            updateHeaderAuthUI();
            closeEditProfileModal();
            showToast("Profile updated successfully!", "success");

            if (currentUser.role === "patient" && typeof updatePatientProfileUI === "function") {
                updatePatientProfileUI();
            }
        } else {
            showToast(data.error || "Failed to update profile.", "error");
        }
    } catch (err) {
        showToast("Error updating profile: " + err.message, "error");
    }
}

function handleLogout() {
    currentUser = null;
    authToken = null;
    localStorage.removeItem("netra_user");
    localStorage.removeItem("netra_token");
    updateHeaderAuthUI();
    showToast("Logged out successfully.", "info");
    navigateTo("landing");
}
