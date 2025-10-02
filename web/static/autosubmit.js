let scanBuffer = "";
let lastKeyTime = 0;
const SCAN_INTERVAL = 50; // 小于这个值认为是扫码枪
const SUBMIT_CODE = "SUBMIT_FORM_NOW";
const form = document.querySelector("#mainForm");

document.addEventListener("keydown", function(event) {
    const now = Date.now();
    const isFastInput = now - lastKeyTime < SCAN_INTERVAL;
    lastKeyTime = now;

    if (event.key === "Enter") {
        const finalCode = scanBuffer.trim();
        console.log("检测到输入:", JSON.stringify(finalCode));

        if (isFastInput) {
            if (finalCode === SUBMIT_CODE) {
                // ✅ 提交码：拦截 & 提交
                event.preventDefault();
                event.stopPropagation();
                console.log("✅ 检测到提交码，触发表单提交");
                if (form) {
                    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                    // === 新增部分：提交之后，让光标回到第一个输入框 ===
                    const firstInput = form.querySelector("input");
                    if (firstInput) {
                        setTimeout(() => firstInput.focus(), 50);
                    }
                }
            } else if (finalCode) {
                // ✅ 普通码：写入输入框，但允许回车照常触发
                const activeEl = document.activeElement;
                if (activeEl && activeEl.tagName === "INPUT") {
                    activeEl.value = finalCode;
                }
                // ⚠️ 注意：这里不调用 preventDefault，让扫码枪的 Enter 照常生效
            }
        }

        scanBuffer = "";
        return;
    }

    // 累积扫码枪输入
    if (event.key.length === 1 && isFastInput) {
        scanBuffer += event.key;
        event.preventDefault();  // 阻止字符进入输入框
        event.stopPropagation();
    }
}, { capture: true });