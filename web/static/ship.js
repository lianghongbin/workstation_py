// ship.js
// 作用：提交出货表单 -> 主进程保存到 SQLite(ship_data)
//      返回结果在表单下方消息区展示（5 秒后自动隐藏）

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("ship-form");
    const msgBox = document.getElementById("ship-error");

    // [MOD] 优先取 iframe 自身的 electronAPI；取不到则回退到父窗口的 electronAPI
    const api =
        (typeof window !== "undefined" && window.electronAPI) ||
        (typeof window !== "undefined" && window.parent && window.parent.electronAPI) ||
        null;

    // 统一的消息显示
    let __timer = null;
    function showMsg(text, ok = false) {
        if (!msgBox) return;
        if (__timer) { clearTimeout(__timer); __timer = null; }
        msgBox.textContent = text || "";
        msgBox.style.display = "block";
        msgBox.style.color = ok ? "#0a7a3d" : "#b00020";
        // 5 秒后淡出
        __timer = setTimeout(() => {
            msgBox.style.display = "none";
            msgBox.textContent = "";
        }, 5000);
    }

    // [MOD] 绑定保存结果事件：
    // 1) 直接监听（当 api 存在时）
    if (api && api.onSaveShipResult) {
        api.onSaveShipResult((res) => {
            if (res && res.success) {
                showMsg("保存成功", true);
                form.reset();
            } else {
                showMsg(res?.message || "保存失败");
            }
        });
    }

    // 2) 兜底：如果父窗口用 postMessage 回传结果，这里也能收到
    window.addEventListener("message", (e) => {
        if (e?.data?.type === "save-shipment-result") {
            const res = e.data.payload;
            if (res && res.success) {
                showMsg("保存成功", true);
                form.reset();
            } else {
                showMsg(res?.message || "保存失败");
            }
        }
    });

    // 表单提交：收集数据 -> IPC 发送到主进程
    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const data = {
            // 和数据库列名一一对应：barcode, cartons, qty, weight, spec, remark
            barcode: (document.getElementById("barcode")?.value || "").trim(),
            cartons: parseInt(document.getElementById("cartons")?.value || "0", 10),
            qty: parseInt(document.getElementById("qty")?.value || "0", 10),
            weight: parseFloat(document.getElementById("weight")?.value || "0"),
            spec: (document.getElementById("spec")?.value || "").trim(),
            remark: (document.getElementById("remark")?.value || "").trim(), // 备注：你刚加的字段
        };

        // 简单校验
        if (!data.barcode) return showMsg("请填写产品条码");
        if (!data.cartons || data.cartons <= 0) return showMsg("请填写有效的箱数");
        if (!data.qty || data.qty <= 0) return showMsg("请填写有效的 QTY");
        if (isNaN(data.weight)) return showMsg("请填写有效的重量");
        if (!data.spec) return showMsg("请填写或选择箱规");

        // [MOD] 优先走 api（iframe 自己或父窗口的 electronAPI）
        if (api && api.sendShip) {
            api.sendShip(data);
            return;
        }

        // [MOD] 再兜底：发给父窗口（如果父窗口做了 postMessage 转发）
        if (window.parent && window.parent !== window) {
            window.parent.postMessage({ type: "save-shipment", payload: data }, "*");
            return;
        }

        // 都不可用才报错
        console.error("electronAPI.sendShip 不可用");
        showMsg("系统错误：预加载接口不可用");
    });
});