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
    const basketState = {}; // {1: {count, deleted}}

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
                json.baskets.forEach(b => {
                    // 🟩 新增 sku 字段带入本地状态，用于 hover
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
    // ✅ 初始化所有篮子（旧逻辑保留）
    // ============================================================
    function initBaskets() {
        basketList.innerHTML = "";
        for (let i = 1; i <= totalBaskets; i++) {
            basketState[i] = {count: basketState[i]?.count || 0, deleted: basketState[i]?.deleted || false};
            basketList.appendChild(createBasketElement(i));
        }
        addBasketButton();
    }

    // ✅ 创建篮子DOM节点
    function createBasketElement(id) {
        const div = document.createElement("div");
        div.className = "basket-item";
        if (basketState[id]?.deleted) div.classList.add("deleted");
        div.id = `basket-${id}`;

        // 🟩 新增
        const s = basketState[id]?.sku;
        div.title = s ? ("SKU: " + s) : "空篮子";

        div.innerHTML = `
            <div>${id}号</div>
            <div class="basket-num">${basketState[id]?.count || 0}</div>
            <!-- 🟩【修改】：最后一个篮子不显示右上角 delete -->
            ${(id !== totalBaskets || basketState[id]?.deleted)
            ? `<span class="basket-delete" data-tip="${basketState[id]?.deleted ? '恢复篮子' : '删除篮子'}">
                ${basketState[id]?.deleted ? '✔' : '×'}
            </span>`
            : ''}

            <!-- ✅ 保留右下角删除 -->
            ${id === totalBaskets
            ? '<span class="basket-remove" data-tip="删除篮子">🗑</span>'
            : ''}
        `;

        const delBtn = div.querySelector(".basket-delete");
        // 🟩【修改】增加存在性判断，防止最后一个篮子没有 delete 按钮时报错
        if (delBtn) {
            if (basketState[id]?.deleted) delBtn.classList.add("restore");

            delBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                handleToggleBasket(id);
            });
        }

        // 🆕【新增功能】：仅最后一个篮子绑定删除事件（右下角 🗑）
        if (id === totalBaskets) {
            const removeBtn = div.querySelector(".basket-remove");
            if (removeBtn) {
                removeBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const confirmed = confirm(`确定要删除 ${id} 号篮子吗？`);
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
            }
        }

        return div;
    }

    // ✅ 添加“+”按钮
    function addBasketButton() {
        const addBtn = document.createElement("div");
        addBtn.className = "basket-add";
        addBtn.textContent = "+";
        addBtn.title = "添加新篮子";
        addBtn.addEventListener("click", async () => {
            // 🔹后端交互：功能2 添加篮子
            await fetch("/sorting/api/basket", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action: "add"})
            });
            await loadFromServer(); // 重新加载最新数据
        });
        basketList.appendChild(addBtn);
    }

    // ✅ 删除 / 恢复切换
    async function handleToggleBasket(id) {
        const basket = basketState[id];
        const el = document.getElementById(`basket-${id}`);
        const btn = el.querySelector(".basket-delete");

        // 🟩 新逻辑：如果删除的是最后一个篮子 -> 彻底删除，而不是置灰
        if (!basket.deleted) {
            const confirmed = confirm(`确定要删除 ${id} 号篮子吗？\n该篮子数量将被重置为 0。`);
            if (!confirmed) return;

            // ✅ 如果是最后一个编号
            if (id === totalBaskets) {
                // 🔹后端交互：功能2 删除最后一个篮子
                await fetch("/sorting/api/basket", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({action: "remove"})
                });
                await loadFromServer();
                return;
            }

            // ✅ 其他篮子照旧置灰
            basket.deleted = true;
            basket.count = 0;
            el.classList.add("deleted");
            el.querySelector(".basket-num").textContent = "0";
            btn.textContent = "✔";
            btn.setAttribute("data-tip", "恢复篮子");
            btn.classList.add("restore");

            // 🔹后端交互：功能3 删除中间篮子
            await fetch("/sorting/api/basket_toggle", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id, action: "delete"})
            });
        } else {
            basket.deleted = false;
            basket.count = 0;
            el.classList.remove("deleted");
            el.querySelector(".basket-num").textContent = "0";
            btn.textContent = "×";
            btn.setAttribute("data-tip", "删除篮子");
            btn.classList.remove("restore");

            // 🔹后端交互：功能3 恢复篮子
            await fetch("/sorting/api/basket_toggle", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id, action: "restore"})
            });
        }
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

            // 🟩 新逻辑：篮子不够的情况（NO_EMPTY）
            if (!json.success && json.reason === "NO_EMPTY") {
                msgBox.textContent = json.message;
                msgBox.className = "form-message error";

                // 🟩 语音提示
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

            // ✅ 原逻辑保持不变
            // ✅ 原逻辑保持不变
            const randomId = json.basket;

            // 🟩 新增：同步写入前端篮子状态里的 sku，用于 hover 显示
            basketState[randomId].sku = json.sku;

            // 🟩 新增：立刻更新该篮子 div 的 title 提示
            const el = document.getElementById(`basket-${randomId}`);
            if (el) el.title = "SKU: " + json.sku;

            basketState[randomId].count++;
            updateBasketDisplay(randomId, basketState[randomId].count);
            flashBasket(randomId);

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
    // 🔹功能 4：重置篮子数量（后端同步）
    // ============================================================
    document.getElementById("resetBaskets").addEventListener("click", async () => {
        const confirmed = confirm("确定要重置所有篮子数量为 0 吗？");
        if (!confirmed) return;

        const res = await fetch("/sorting/api/reset", {method: "POST"});
        const json = await res.json();
        if (json.success) {
            for (const id in basketState) {
                basketState[id].count = 0;
                const el = document.getElementById(`basket-${id}`);
                if (el) {
                    const num = el.querySelector(".basket-num");
                    if (num) num.textContent = "0";
                }
            }
            msgBox.textContent = json.message;
            msgBox.className = "form-message success";
        }
    });

    // ✅ 页面加载后执行：从后端加载真实数据
    loadFromServer();

    // ✅ 输入框焦点控制（原逻辑保留）
    setInterval(() => {
        if (document.activeElement !== skuInput) {
            skuInput.focus();
        }
    }, 1000);

    skuInput.addEventListener("focus", () => {
        if (skuInput.value.length > 0) {
            skuInput.select();
        }
    });

    skuInput.addEventListener("blur", () => {
        setTimeout(() => {
            skuInput.focus();
            skuInput.select();
        }, 100);
    });
});

// ============================================================
// ✅ 最近分配记录（支持后端返回 logs）
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

// 🔹后端返回日志时直接渲染
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