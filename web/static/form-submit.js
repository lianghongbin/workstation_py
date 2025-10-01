function initFormSubmit(url, formName) {
    const form = document.getElementById(formName);
    const messageContainerId = "formMessage";

    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault(); // 阻止默认刷新

        const formData = new FormData(form);
        const plainData = Object.fromEntries(formData.entries());  // 转成普通对象

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ fields: plainData })
            });

            const result = await response.json();

            if (result.success) {
                showMessage(messageContainerId, true, result.message || "操作成功");
                form.reset();
            } else {
                showMessage(messageContainerId, false, result.message || "操作失败");
            }
        } catch (error) {
            console.error(error);
            showMessage(messageContainerId, false, error || "请求出错，请稍后再试");
        }
    });
}