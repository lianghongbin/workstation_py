document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('mainForm');

    // !!! 请在此设置您的特定提交码 !!!
    const SUBMIT_CODE = "SUBMIT_FORM_NOW";

    let scanBuffer = '';    // 用于缓存扫码字符
    let scanTimer = null;   // 用于判断输入速度的计时器
    const TYPING_TIMEOUT = 50; // 毫秒 (阈值：50ms 内连续输入视为扫码枪)

    // --- 核心全局键盘监听逻辑 ---
    document.addEventListener('keydown', function(event) {

        // 1. 清除旧计时器，只要有新键按下，就认为输入在继续
        clearTimeout(scanTimer);

        // 2. 检测结束符 (回车)
        if (event.key === 'Enter' || event.keyCode === 13) {

            const finalCode = scanBuffer.trim(); // 获取完整的扫码结果

            // --- 核心判断逻辑：只在匹配特定提交码时操作 ---
            if (finalCode === SUBMIT_CODE) {

                // 阻止这个回车的默认行为，确保它只执行提交，不干扰其他 JS 或默认跳转逻辑
                event.preventDefault();

                console.log(`全局检测到特定提交码: ${finalCode}，正在触发表单提交...`);

                // 触发您已有的 AJAX 提交事件
                form.dispatchEvent(new Event('submit'));

            }

            // 无论是提交还是非提交，都清除当前缓存，等待下一轮扫码
            scanBuffer = '';
            scanTimer = null;

        } else if (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
            // 3. 收集字符：添加到缓存

            scanBuffer += event.key;

            // 设置新的计时器：如果超时，清空缓存（判断为人工打字）
            scanTimer = setTimeout(() => {
                scanBuffer = '';
                scanTimer = null;
            }, TYPING_TIMEOUT);
        }

        // 4. 其他普通回车事件（不匹配 SUBMIT_CODE 的回车）：
        //    我们不调用 event.preventDefault()，也不添加任何其他逻辑，
        //    让它们继续执行页面上其他 JS 实现的光标跳转功能。

    }, { capture: true }); // 使用 capture: true 可以确保我们的监听器在 DOM 捕获阶段就运行，提高拦截优先级。
});