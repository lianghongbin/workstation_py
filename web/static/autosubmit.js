let scanBuffer = "";
let lastKeyTime = 0;
const SCAN_INTERVAL = 50; // 小于这个值认为是扫码枪
const SUBMIT_CODE = "SUBMIT_FORM_NOW";
const ABNORMAL_CODE = "__ABNORMAL__";
const form = document.querySelector("#mainForm");

document.addEventListener("keydown", function(event) {
    const now = Date.now();
    const isFastInput = now - lastKeyTime < SCAN_INTERVAL;
    lastKeyTime = now;

    if (event.key === "Enter") {
        const finalCode = scanBuffer.trim();
        console.log("检测到输入:", JSON.stringify(finalCode));

        if (isFastInput) {

            // 🟢 新增逻辑：当扫码内容是 "abnormal" + 回车时，勾选异常复选框
            if (finalCode.toLowerCase() === ABNORMAL_CODE) {
                event.preventDefault();
                event.stopPropagation();
                console.log("⚠️ 检测到异常扫码: abnormal + Enter");

                const prevActive = document.activeElement; // 🟢 记录之前光标所在位置
                const checkbox = document.getElementById("abnormal");
                if (checkbox) {
                    checkbox.checked = true; // ✅ 自动勾选异常
                    console.log("✅ 已勾选异常复选框");
                }

                // 🟢 恢复光标到原输入框
                if (prevActive && typeof prevActive.focus === "function") {
                    setTimeout(() => prevActive.focus(), 50);
                }

                scanBuffer = ""; // 清空缓存
                return; // 🟢 阻止后续执行（不触发表单提交）
            }

            // === 以下保持原逻辑 ===
            if (finalCode === SUBMIT_CODE) {
                event.preventDefault();
                event.stopPropagation();
                console.log("✅ 检测到提交码，触发表单提交");
                if (form) {
                    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                    const firstInput = form.querySelector("input");
                    if (firstInput) {
                        setTimeout(() => firstInput.focus(), 50);
                    }
                }
            } else if (finalCode) {
                const activeEl = document.activeElement;
                if (activeEl && activeEl.tagName === "INPUT") {
                    activeEl.value = finalCode;
                }
                // ⚠️ 不阻止默认回车，让扫码枪行为自然执行
            }
        }

        scanBuffer = "";
        return;
    }

    // 累积扫码枪输入（只记录字符，不处理）
    if (event.key.length === 1 && isFastInput) {
        scanBuffer += event.key;
        event.preventDefault();  // 阻止输入框直接显示扫码字符
        event.stopPropagation();
    }
}, { capture: true });