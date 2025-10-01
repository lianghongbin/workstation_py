function showMessage(elementId, success, message) {
    const el = document.getElementById(elementId);
    el.style.display = "block";
    el.className = "form-message " + (success ? "is-success" : "is-error");
    el.textContent = message;
}