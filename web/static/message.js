// ✅ 页面加载后自动聚焦第一个输入框
document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("#mainForm");
  const target = form?.querySelector("input, textarea, select");
  if (!target) return;

  /** 保持焦点并选中所有内容 */
  const focusAndSelectAll = () => {
    if (document.activeElement !== target) {
      target.focus({ preventScroll: true });
    }
    if (target.value && typeof target.setSelectionRange === "function") {
      target.setSelectionRange(0, target.value.length);
    }
  };

  // ✅ 初始聚焦并选中
  focusAndSelectAll();

  // ✅ 一旦失焦，立即重新聚焦
  target.addEventListener("blur", () => {
    setTimeout(focusAndSelectAll, 0);
  });

  // ✅ 只在鼠标点击或粘贴后保持全选，避免输入时不断覆盖
    ["paste", "mouseup"].forEach(evt => {
      target.addEventListener(evt, () => {
        if (target.value) {
          target.setSelectionRange(0, target.value.length);
        }
      });
    });

  // ✅ 标签页切回或窗口激活时重新聚焦
  window.addEventListener("focus", focusAndSelectAll);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") focusAndSelectAll();
  });
});

/**
 * ✅ 统一消息提示组件
 * @param {string} elementId - 容器元素ID
 * @param {boolean} success - 是否成功
 * @param {string} message - 提示内容
 */
function showMessage(elementId, success, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.style.display = "block";
  el.className = "form-message " + (success ? "is-success" : "is-error");
  el.textContent = message;

  // ✅ 播放声音提示
  try {
    // 如果你有自己的音频文件，可以放在 static/sounds/ 下
    const audio = new Audio(success ? "/static/sounds/success.wav" : "/static/sounds/fail.wav");
    audio.volume = 0.6; // 音量适中
    audio.play().catch(() => {
      // 某些浏览器阻止自动播放，忽略即可
    });
  } catch (err) {
    console.warn("声音播放失败：", err);
  }
}