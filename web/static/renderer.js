// renderer.js
// 仅新增/修正“登录浮层会话控制（重启或 1 小时无操作需重新登录）”。
// 其它逻辑（手动同步、菜单+面包屑、iframe postMessage 桥接）保持不变。

document.addEventListener('DOMContentLoaded', () => {
    /** ------------------ 登录浮层（你已有逻辑的基础上增强） ------------------ */
    const overlay = document.getElementById('login-overlay');
    const form = document.getElementById('login-form');
    const userInput = document.getElementById('login-username');
    const passInput = document.getElementById('login-password');

    // [MOD] 会话控制相关的常量与工具函数（新增）
    const LOGIN_FLAG = '__logged_in__';
    const LAST_ACTIVITY = '__last_activity__';
    const BOOT_ID = '__boot_id__';
    const MAX_IDLE_MS = 60 * 60 * 1000; // 1 小时无操作过期

    // [MOD] 本次应用启动的“会话标识”（仅存 sessionStorage，重启会变化）
    let sessionBootId = sessionStorage.getItem(BOOT_ID);
    if (!sessionBootId) {
        sessionBootId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        sessionStorage.setItem(BOOT_ID, sessionBootId);
    }

    // [MOD] 显隐登录浮层的两个小工具
    const showLogin = () => overlay?.setAttribute('aria-hidden', 'false');
    const hideLogin = () => overlay?.setAttribute('aria-hidden', 'true');

    // [MOD] 记录活跃时间
    const markActivity = () => localStorage.setItem(LAST_ACTIVITY, String(Date.now()));

    // [MOD] 统一检查是否需要要求重新登录（重启或超时）
    const enforceLoginState = () => {
        const loggedIn = localStorage.getItem(LOGIN_FLAG) === '1';
        const lastAct = parseInt(localStorage.getItem(LAST_ACTIVITY) || '0', 10);
        const storedBoot = localStorage.getItem(BOOT_ID);
        const now = Date.now();

        const idleTooLong = !lastAct || (now - lastAct > MAX_IDLE_MS);
        const restarted = storedBoot !== sessionBootId; // 重启则 sessionBootId 变化

        if (!loggedIn || idleTooLong || restarted) {
            // 需要登录：清理并显示浮层
            localStorage.removeItem(LOGIN_FLAG);
            localStorage.removeItem(LAST_ACTIVITY);
            localStorage.removeItem(BOOT_ID);
            showLogin();
        } else {
            hideLogin();
        }
    };

    if (overlay && form) {
        // [MOD] 启动即检查一次（重启或超时则要求登录）
        enforceLoginState(); // —— 新增调用

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const u = (userInput?.value || '').trim();
            const p = (passInput?.value || '').trim();
            if (u === '810' && p === '5188') {
                // [MOD] 登录成功：标记登录 + 写入活跃时间 + 绑定当前启动ID
                localStorage.setItem(LOGIN_FLAG, '1');
                localStorage.setItem(LAST_ACTIVITY, String(Date.now()));
                localStorage.setItem(BOOT_ID, sessionBootId); // 重启后将不相等，触发重新登录
                passInput.value = '';

                hideLogin();
            } else {
                alert('账号或密码错误');
            }
        });

        // [MOD] 监听用户活动，刷新活跃时间（仅在已登录且浮层隐藏时）
        ['click', 'keydown', 'mousemove', 'scroll', 'focus'].forEach(evt => {
            document.addEventListener(evt, () => {
                if (overlay?.getAttribute('aria-hidden') === 'true' &&
                    localStorage.getItem(LOGIN_FLAG) === '1') {
                    markActivity();
                }
            }, { passive: true });
        });

        // [MOD] 定时轮询（每 60 秒）检查是否超时或重启
        setInterval(enforceLoginState, 60 * 1000);
    }

    /** ------------------ 立即同步（保持不变，仅确保 ID 一致） ------------------ */
        // 修正点1：main.html 的按钮 id 是 sync-now-btn
    const syncBtn = document.getElementById('sync-now-btn');
    if (syncBtn && window.electronAPI?.manualSync) {
        syncBtn.addEventListener('click', () => {
            console.log('[Renderer] 点击立即同步');
            // preload.js 内把 channel 映射到主进程的 "run-sync-now"
            window.electronAPI.manualSync();
        });
    }

    // 主进程会通过 "sync-result" 回传结果；preload 需暴露 onSyncResult
    if (window.electronAPI?.onSyncResult) {
        window.electronAPI.onSyncResult((res) => {
            console.log('[Renderer] 收到同步结果:', res);
            alert(res?.message || (res?.success ? '同步完成' : '同步失败'));
        });
    }

    /** ------------------ 左侧菜单切换 + 面包屑（保持不变） ------------------ */
    const menuItems = document.querySelectorAll('.menu-item');
    const iframe = document.getElementById('content-frame');
    const breadcrumb = document.getElementById('breadcrumb');

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.getAttribute('href');
            const bc = item.getAttribute('data-breadcrumb');

            if (iframe) iframe.src = page;              // 切换右侧工作区页面
            if (breadcrumb) breadcrumb.textContent = bc; // 更新面包屑

            // 菜单高亮
            menuItems.forEach(li => li.classList.remove('active'));
            item.classList.add('active');
        });
    });
    if (menuItems.length > 0) menuItems[0].classList.add('active');



    /** ------------------ 出货保存、查询 postMessage 桥接（新增） ------------------ */
// 场景：iframe(ship-query.html) 中拿不到 window.electronAPI
// 这时它会 postMessage 到父窗口。这里把查询请求转发到主进程，
// 并把查询结果再 postMessage 回 iframe。
    window.addEventListener('message', async (e) => {
        const data = e?.data;
        if (!data || typeof data !== 'object') return;

        // [原有] 子页面请求保存收货
        if (data.type === 'save-receive' && data.data) {
            if (window.electronAPI?.sendReceive) {
                window.electronAPI.sendReceive(data.data);
            }
        }

        // [新增] 子页面请求查询出货
        if (data.type === 'query-shipment-data' && data.params && data.channel) {
            if (window.electronAPI?.queryShipmentData) {
                try {
                    const result = await window.electronAPI.queryShipmentData(data.params);
                    console.log('[Renderer] 查询结果:', result);
                    // 转发回 iframe（带上 channel 匹配）
                    e.source.postMessage({
                        type: 'query-shipment-result',
                        result,
                        channel: data.channel
                    }, '*');
                } catch (err) {
                    console.error('[Renderer] 查询失败:', err);
                    e.source.postMessage({
                        type: 'query-shipment-result',
                        result: { error: err.message },
                        channel: data.channel
                    }, '*');
                }
            }
        }

        // [新增] 子页面请求打印面单
        if (data.type === 'print-label' && data.record && data.channel) {
            if (window.electronAPI?.printLabel) {
                try {
                    await window.electronAPI.printLabel(data.record);
                    console.log('[Renderer] 打印任务提交成功');
                    e.source.postMessage({
                        type: 'print-label-result',
                        result: { success: true },
                        channel: data.channel
                    }, '*');
                } catch (err) {
                    console.error('[Renderer] 打印失败:', err);
                    e.source.postMessage({
                        type: 'print-label-result',
                        result: { error: err.message },
                        channel: data.channel
                    }, '*');
                }
            }
        }
    });

    // 当 preload 把 "save-receive-result" 事件转给前端时，
    // 我们再把结果转发给当前工作区 iframe，这样 receiver.html 的降级监听能收到。
    if (window.electronAPI?.onSaveReceiveResult) {
        window.electronAPI.onSaveReceiveResult((result) => {
            console.log('[Renderer] 转发保存结果到 iframe:', result);
            const frame = document.getElementById('content-frame');
            if (frame?.contentWindow) {
                frame.contentWindow.postMessage({ type: 'save-receive-result', result }, '*');
            }
        });
    }

    /** ------------------ 退出登录 ------------------ */
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('[Renderer] 用户点击退出登录');
            localStorage.removeItem(LOGIN_FLAG);
            localStorage.removeItem(LAST_ACTIVITY);
            localStorage.removeItem(BOOT_ID);
            passInput.value = '';

            showLogin(); // 重新显示登录浮层
        });
    }
});