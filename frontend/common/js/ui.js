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
