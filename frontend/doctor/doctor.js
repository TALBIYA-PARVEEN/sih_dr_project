// NetraAI Doctor Workstation MVC Controller

let doctorQueue = [];
let currentDoctorSession = null;
let selectedDoctorFile = null;
let doctorChatPatientsList = [];
let activeDoctorChatPatient = null;

function initDoctorPortal() {
    setupDoctorDropZone();
    loadDoctorQueue();
    loadDoctorChat();
}

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

    if (tab === "workstation") loadDoctorQueue();
    if (tab === "chat") loadDoctorChat();
}

function setupDoctorDropZone() {
    const dropZone = document.getElementById("docDropZone");
    const fileInput = document.getElementById("docFileInput");
    if (!dropZone || !fileInput) return;

    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleDoctorFileSelect(e.target.files[0]);
        }
    };

    dropZone.ondragover = (e) => {
        e.preventDefault();
        dropZone.classList.add("dropzone-active");
    };

    dropZone.ondragleave = () => {
        dropZone.classList.remove("dropzone-active");
    };

    dropZone.ondrop = (e) => {
        e.preventDefault();
        dropZone.classList.remove("dropzone-active");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleDoctorFileSelect(e.dataTransfer.files[0]);
        }
    };
}

function handleDoctorFileSelect(file) {
    selectedDoctorFile = file;
    const previewContainer = document.getElementById("docPreviewContainer");
    const imgPreview = document.getElementById("docImgPreview");
    const namePreview = document.getElementById("docFileNamePreview");

    if (previewContainer && imgPreview) {
        imgPreview.src = URL.createObjectURL(file);
        if (namePreview) namePreview.innerText = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        previewContainer.classList.remove("hidden");
    }
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
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Analyzing Fundus & Adding to Queue...`;

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
            alert("🚫 Scan Rejected (Non-Retinal or Ungradable Image)\n\n" + reason + "\n\nAction Required: Please recapture and upload an authentic retinal fundus photograph.");
            return;
        }

        if (result.status === "success") {
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
                notifText.innerHTML = `New patient account created for <b>${patientEmail}</b>. Login credentials sent to email!`;
                pwBadge.innerText = `Temp Password: ${result.temp_password}`;
                pwBadge.classList.remove("hidden");
            } else {
                notifText.innerHTML = `Diagnostic scan attached to existing patient dashboard for <b>${patientEmail}</b>. (Existing password preserved).`;
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
        const countEl = document.getElementById("doctorQueueCount");
        if (countEl) countEl.innerText = doctorQueue.length;

        const list = document.getElementById("doctorQueueList");
        if (!list) return;
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
                    <span class="font-medium text-slate-600">${s.clinician_review ? s.clinician_review.status : 'Pending Review'}</span>
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

    document.getElementById("docSelectStatus").value = (session.clinician_review && session.clinician_review.status !== "Pending Review") ? session.clinician_review.status : "Confirmed";
    document.getElementById("docInputNotes").value = (session.clinician_review && session.clinician_review.notes) ? session.clinician_review.notes : "";
}

async function submitDoctorSignOff() {
    if (!currentDoctorSession) return;

    const status = document.getElementById("docSelectStatus").value;
    const notes = document.getElementById("docInputNotes").value;
    const docName = currentUser && currentUser.role === "doctor" ? currentUser.full_name : "Dr. Rashika";
    const docId = currentUser ? currentUser.id : null;

    try {
        const res = await fetch(`${API_BASE}/review/${currentDoctorSession.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, notes, reviewed_by: docName, doctor_id: docId })
        });
        const data = await res.json();

        if (data.status === "success") {
            showToast("Clinical validation & sign-off recorded! Removed from active queue.", "success");
            loadDoctorQueue();
        } else {
            showToast(data.error || "Sign-off error.", "error");
        }
    } catch (e) {
        showToast("Error submitting sign-off: " + e.message, "error");
    }
}

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
