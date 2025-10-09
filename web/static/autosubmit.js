let scanBuffer = "";
let lastKeyTime = 0;
const SCAN_INTERVAL = 50; // 小于这个值认为是扫码枪
const SUBMIT_CODE = "SUBMIT_FORM_NOW";
const form = document.querySelector("#mainForm");

// ✅ 新增：通用解析函数，只提取最后一段括号数字+内容
function normalizeBarcode(raw) {
    const matches = [...raw.matchAll(/\((\d+)\)(\d+)/g)];
    if (matches.length === 0) return raw; // 非GS1格式则原样返回
    const last = matches[matches.length - 1];
    return last[1] + last[2];
}

document.addEventListener("keydown", function(event) {
    const now = Date.now();
    const isFastInput = now - lastKeyTime < SCAN_INTERVAL;
    lastKeyTime = now;

    if (event.key === "Enter") {
        const finalCode = scanBuffer.trim();
        console.log("检测到输入:", JSON.stringify(finalCode));

        if (isFastInput) {

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

                    // ✅ 【新增功能】在赋值前检查是否是带括号的 GS1 条码格式
                    let normalized = finalCode;
                    if (/\(\d+\)\d+\(\d+\)\d+/.test(finalCode)) {
                        normalized = normalizeBarcode(finalCode);
                        console.log("识别为 GS1 格式，自动转换:", normalized);
                    }

                    // ✅ 仍然使用原逻辑赋值
                    activeEl.value = normalized;

                    // ✅ 扫码赋值后自动全选（仅扫码时执行，不影响人工输入）
                    setTimeout(() => {
                        if (typeof activeEl.setSelectionRange === "function") {
                            activeEl.setSelectionRange(0, activeEl.value.length);
                        }
                    }, 0);
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