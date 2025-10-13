// ============================================================
// 🧩 智能分拣系统前端逻辑（sorting.js）
// 与 Flask 后端 sorting.py 对应的 5 个交互接口：
//
// 1️⃣ 页面初始化：/sorting/api/init
// 2️⃣ 添加 / 删除最后一个篮子：/sorting/api/basket
// 3️⃣ 删除 / 恢复中间篮子：/sorting/api/basket_toggle
// 4️⃣ 重置所有篮子：/sorting/api/reset
// 5️⃣ 扫码或输入 SKU 分配篮子：/sorting/api/assign
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("scanForm");
    const skuInput = document.getElementById("skuInput");
    const boxNumber = document.getElementById("boxNumber");
    const skuLabel = document.getElementById("skuLabel");
    const msgBox = document.getElementById("formMessage");
    const basketList = document.getElementById("basketList");

    let totalBaskets = 50; // 初始50个篮子
    const basketState = {}; // {1: {count, deleted, sku}}

    // ============================================================
    // 🔹功能 1：页面加载时从后端获取当前篮子状态和日志
    // ============================================================
    async function loadFromServer() {
        try {
            const res = await fetch("/sorting/api/init");
            const json = await res.json();
            if (json.success) {
                totalBaskets = json.baskets.length;
                basketList.innerHTML = "";
                json.baskets.forEach((b) => {
                    basketState[b.id] = { count: b.count, deleted: b.deleted, sku: b.sku || null };
                    basketList.appendChild(createBasketElement(b.id));
                });
                addBasketButton();
                renderHistoryFromServer(json.logs || []);
            }
        } catch (err) {
            console.error("❌ 初始化加载失败：", err);
        }
    }

    // ============================================================
    // ✅ 创建篮子DOM节点（本次主要修改）
    // ============================================================
    function createBasketElement(id) {
        const div = document.createElement("div");
        div.className = "basket-item";
        if (basketState[id]?.deleted) div.classList.add("deleted");
        if (basketState[id]?.sku) div.classList.add("has-sku");
        div.id = `basket-${id}`;

        const s = basketState[id]?.sku;
        div.title = s ? ("SKU: " + s) : "空篮子";

        // ✅ 每个篮子都带 × 禁用/恢复 按钮
        div.innerHTML = `
            <div>${id}号</div>
            <div class="basket-num">${basketState[id]?.count || 0}</div>
            <span class="basket-delete" data-tip="${basketState[id]?.deleted ? '恢复篮子' : '禁用篮子'}">
                ${basketState[id]?.deleted ? '✔' : '×'}
            </span>
        `;

        // ✅ 仅最后一个篮子额外加 🗑 删除按钮
        if (id === totalBaskets) {
            const removeIcon = document.createElement("span");
            removeIcon.className = "basket-remove";
            removeIcon.textContent = "🗑";
            removeIcon.setAttribute("data-tip", "删除最后一个篮子");
            removeIcon.addEventListener("click", async (e) => {
                e.stopPropagation();
                const confirmed = confirm(`确定要彻底删除 ${id} 号篮子吗？`);
                if (!confirmed) return;
                const res = await fetch("/sorting/api/basket", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({action: "remove"})
                });
                const json = await res.json();
                if (json.success) await loadFromServer();
                else alert("删除失败，请重试。");
            });
            div.appendChild(removeIcon);
        }

        // ✅ 禁用/恢复按钮逻辑
        const delBtn = div.querySelector(".basket-delete");
        if (delBtn) {
            // 如果篮子内有 SKU，则禁用按钮
            if (basketState[id]?.sku) {
                delBtn.classList.add("disabled");
                delBtn.style.pointerEvents = "none";
                delBtn.style.opacity = "0.5";
            }

            delBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                handleToggleBasket(id);
            });
        }

         // 🟩 新增：双击篮子清空 SKU 与数量
    div.addEventListener("dblclick", async (e) => {
        e.stopPropagation();
        const confirmed = confirm(`确定要清空 ${id} 号篮子吗？`);
        if (!confirmed) return;

        // 清空前端状态
        basketState[id].sku = null;
        basketState[id].count = 0;

        const numEl = div.querySelector(".basket-num");
        if (numEl) numEl.textContent = "0";
        div.classList.remove("has-sku");
        div.title = "空篮子";

        // 通知后端（保持风格一致）
        await fetch("/sorting/api/basket_toggle", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id, action: "clear"})
        });
    });

        return div;
    }

    // ✅ 添加“+”按钮
    function addBasketButton() {
        const addBtn = document.createElement("div");
        addBtn.className = "basket-add";
        addBtn.textContent = "+";
        addBtn.title = "添加新篮子";
        addBtn.addEventListener("click", async () => {
            await fetch("/sorting/api/basket", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action: "add"})
            });
            await loadFromServer();
        });
        basketList.appendChild(addBtn);
    }

    // ============================================================
    // ✅ 删除 / 恢复切换逻辑（保持数量与 SKU）
    // ============================================================
    async function handleToggleBasket(id) {
        const basket = basketState[id];
        const el = document.getElementById(`basket-${id}`);
        const btn = el.querySelector(".basket-delete");

        if (!basket || !btn) return;

        // 🟨 禁用逻辑
        if (!basket.deleted) {
            if (basket.sku) {
                alert("此篮子内有SKU，无法禁用。");
                return;
            }
            const confirmed = confirm(`确定要禁用 ${id} 号篮子吗？`);
            if (!confirmed) return;

            basket.deleted = true;
            el.classList.add("deleted");
            btn.textContent = "✔";
            btn.setAttribute("data-tip", "恢复篮子");
            btn.classList.add("restore");

            await fetch("/sorting/api/basket_toggle", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id, action: "delete"})
            });
            return;
        }

        // 🟩 恢复逻辑：保留数量与 SKU
        const confirmed = confirm(`确定要恢复 ${id} 号篮子吗？`);
        if (!confirmed) return;

        basket.deleted = false;
        el.classList.remove("deleted");
        btn.textContent = "×";
        btn.setAttribute("data-tip", "禁用篮子");
        btn.classList.remove("restore");

        await fetch("/sorting/api/basket_toggle", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id, action: "restore"})
        });
    }

    // ✅ 数量更新
    function updateBasketDisplay(id, count) {
        const el = document.getElementById(`basket-${id}`);
        if (!el) return;
        const num = el.querySelector(".basket-num");
        if (num) num.textContent = count;
    }

    // ✅ 扫码高亮
    function flashBasket(id) {
        const el = document.getElementById(`basket-${id}`);
        if (!el) return;
        el.classList.add("flash");
        setTimeout(() => el.classList.remove("flash"), 600);
    }

    // ============================================================
    // 🔹功能 5：扫码 / 输入 SKU 分配篮子（与后端交互）
    // ============================================================
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const sku = skuInput.value.trim();
        if (!sku) return;

        try {
            const res = await fetch("/sorting/api/assign", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({sku})
            });
            const json = await res.json();

            if (!json.success && json.reason === "NO_EMPTY") {
                msgBox.textContent = json.message;
                msgBox.className = "form-message error";
                const msg = new SpeechSynthesisUtterance(json.message);
                msg.lang = 'zh-CN';
                msg.rate = 1.0;
                speechSynthesis.speak(msg);
                return;
            }

            if (!json.success) {
                alert(json.message || "分配失败");
                return;
            }

            const randomId = json.basket;

            basketState[randomId].sku = json.sku;
            basketState[randomId].count++;
            updateBasketDisplay(randomId, basketState[randomId].count);
            flashBasket(randomId);

            const el = document.getElementById(`basket-${randomId}`);
            if (el) {
                el.title = "SKU: " + json.sku;
                el.classList.add("has-sku");
                const delBtn = el.querySelector(".basket-delete");
                if (delBtn) {
                    delBtn.classList.add("disabled");
                    delBtn.style.pointerEvents = "none";
                    delBtn.style.opacity = "0.5";
                }
            }

            boxNumber.textContent = randomId;
            boxNumber.classList.add("flash");
            setTimeout(() => boxNumber.classList.remove("flash"), 600);

            skuLabel.textContent = `SKU：${sku}`;
            msgBox.textContent = `分配到 ${randomId} 号篮`;
            msgBox.className = "form-message success";

            renderHistoryFromServer(json.logs || []);
            const msg = new SpeechSynthesisUtterance(`${randomId} 号篮`);
            msg.lang = 'zh-CN';
            msg.rate = 1.05;
            speechSynthesis.speak(msg);

            skuInput.value = "";
            skuInput.focus();

        } catch (err) {
            console.error("❌ 分配失败：", err);
        }
    });

    // ============================================================
    // 🔹功能 4：重置篮子数量
    // ============================================================
    document.getElementById("resetBaskets").addEventListener("click", async () => {
        const confirmed = confirm("确定要重置所有篮子数量为 0 吗？");
        if (!confirmed) return;

        const res = await fetch("/sorting/api/reset", {method: "POST"});
        const json = await res.json();
        if (json.success) {
            for (const id in basketState) {
                basketState[id].count = 0;
                basketState[id].sku = null;
                const el = document.getElementById(`basket-${id}`);
                if (el) {
                    const num = el.querySelector(".basket-num");
                    if (num) num.textContent = "0";
                    el.classList.remove("has-sku");
                    el.title = "空篮子";
                }
            }
            msgBox.textContent = json.message;
            msgBox.className = "form-message success";
            await loadFromServer();
        }
    });

    // ✅ 页面加载后执行
    loadFromServer();

    // ✅ 输入框自动聚焦
    setInterval(() => {
        if (document.activeElement !== skuInput) skuInput.focus();
    }, 1000);

    skuInput.addEventListener("focus", () => {
        if (skuInput.value.length > 0) skuInput.select();
    });

    skuInput.addEventListener("blur", () => {
        setTimeout(() => {
            skuInput.focus();
            skuInput.select();
        }, 100);
    });
});

// ============================================================
// ✅ 最近分配记录
// ============================================================
const historyList = document.getElementById("historyList");
const historyData = [];

function updateHistory(sku, basketId) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', {hour12: false});
    const record = `${timeStr} ｜ ${sku} → ${basketId}号篮`;
    historyData.unshift(record);
    if (historyData.length > 5) historyData.pop();
    renderHistory();
}

function renderHistoryFromServer(logs) {
    historyList.innerHTML = logs.slice(0, 5)
        .map(item => `<li>${item.time} ｜ ${item.sku} → ${item.basket}号篮</li>`)
        .join("");
}

function renderHistory() {
    historyList.innerHTML = historyData
        .map(item => `<li>${item}</li>`)
        .join("");
}