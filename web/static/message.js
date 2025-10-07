document.addEventListener("DOMContentLoaded", function() {
    // ✅ 找到 mainForm 中的第一个可输入元素（input 或 textarea）
    const form = document.querySelector("#mainForm");
    if (form) {
        const firstInput = form.querySelector("input, textarea, select");
        if (firstInput) {
            firstInput.focus();
        }
    }
});

function showMessage(elementId, success, message) {
    const el = document.getElementById(elementId);
    el.style.display = "block";
    el.className = "form-message " + (success ? "is-success" : "is-error");
    el.textContent = message;
}