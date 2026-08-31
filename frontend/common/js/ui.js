// NetraAI UI Utilities & Toast Alerts

function showToast(message, type = "info") {
    const toast = document.getElementById("globalToast");
    const toastMsg = document.getElementById("globalToastMessage");
    const toastIcon = document.getElementById("globalToastIcon");
    if (!toast || !toastMsg) {
        console.log(`[Toast ${type}]:`, message);
        return;
    }

    toastMsg.innerText = message;
    toast.className = "fixed bottom-6 right-6 z-50 px-5 py-3.5 rounded-2xl shadow-2xl flex items-center space-x-3 text-xs font-bold transition transform duration-300 pointer-events-auto";

    if (type === "success") {
        toast.classList.add("bg-emerald-600", "text-white");
        if (toastIcon) toastIcon.className = "fa-solid fa-circle-check text-base";
    } else if (type === "error") {
        toast.classList.add("bg-rose-600", "text-white");
        if (toastIcon) toastIcon.className = "fa-solid fa-circle-exclamation text-base";
    } else if (type === "warning") {
        toast.classList.add("bg-amber-500", "text-white");
        if (toastIcon) toastIcon.className = "fa-solid fa-triangle-exclamation text-base";
    } else {
        toast.classList.add("bg-indigo-600", "text-white");
        if (toastIcon) toastIcon.className = "fa-solid fa-circle-info text-base";
    }

    toast.classList.remove("hidden", "opacity-0", "translate-y-4");
    toast.classList.add("opacity-100", "translate-y-0");

    setTimeout(() => {
        toast.classList.remove("opacity-100", "translate-y-0");
        toast.classList.add("opacity-0", "translate-y-4");
        setTimeout(() => toast.classList.add("hidden"), 300);
    }, 4500);
}

function updateHeaderAuthUI() {
    const user = currentUser;
    const authLoggedOut = document.getElementById("headerLoggedOut");
    const authLoggedIn = document.getElementById("headerLoggedIn");
    const headerUserRole = document.getElementById("headerUserRole");
    const headerUserName = document.getElementById("headerUserName");

    if (user) {
        if (authLoggedOut) authLoggedOut.classList.add("hidden");
        if (authLoggedIn) authLoggedIn.classList.remove("hidden");
        if (headerUserName) headerUserName.innerText = user.full_name || user.username;
        if (headerUserRole) {
            headerUserRole.innerText = user.role.toUpperCase();
            if (user.role === "doctor") {
                headerUserRole.className = "text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full uppercase";
            } else if (user.role === "admin") {
                headerUserRole.className = "text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded-full uppercase";
            } else {
                headerUserRole.className = "text-[10px] bg-indigo-100 text-indigo-800 font-bold px-2 py-0.5 rounded-full uppercase";
            }
        }
    } else {
        if (authLoggedOut) authLoggedOut.classList.remove("hidden");
        if (authLoggedIn) authLoggedIn.classList.add("hidden");
    }
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
