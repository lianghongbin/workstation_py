let currentRecord = null; // 覆盖层中正在查看/打印的记录

// === 公开的全局函数：与 ship-query.html 上的 onclick 保持一致 ===
window.showOverlay = function showOverlay(record) {
    currentRecord = record;
    const overlay = document.getElementById("overlay");
    const preview = document.getElementById("labelPreview");

    if (preview) {
        preview.innerHTML = `
        <table class="label-table">
          <tr><th>产品条码</th><td>${record.barcode || ""}</td></tr>
          <tr><th>箱数</th><td>${record.cartons || ""}</td></tr>
          <tr><th>数量</th><td>${record.qty || ""}</td></tr>
          <tr><th>重量</th><td>${record.weight || ""} lb</td></tr>
          <tr><th>箱规</th><td>${record.spec || ""}</td></tr>
          <tr><th>备注</th><td>${record.remark || ""}</td></tr>
        </table>
      `;
    }
    overlay.style.display = "flex";
};

window.closeOverlay = function closeOverlay() {
    const overlay = document.getElementById("overlay");
    overlay.style.display = "none";
};

window.printLabel = async function printLabel(record) {
    // 允许 ship-query.html 里直接调用 printLabel()（无参），则使用当前记录
    const payload = {record: record || currentRecord};
    if (!payload.record) {
        alert("没有可打印的记录");
        return;
    }

    const resp = await fetch("/ship_query/api/print", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok || data.error) {
        throw new Error(data.error || `打印接口返回错误 (${resp.status})`);
    }
    // 若未来需要触发浏览器打印，可在此 window.print() 或打开新窗口
    return data;
};

window.shipProcessed = async function shipProcessed(record) {
    const payload = {record: record || currentRecord};
    if (!payload.record) {
        alert("没有可处理的记录");
        return;
    }

    const resp = await fetch("/ship_query/process", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok || data.error) {
        throw new Error(data.error || `处理申请的接口返回错误 (${resp.status})`);
    }

    return data;
};

function handleClick(action, el) {
    const row = el.closest("tr");
    const id = row.dataset.id;

    // 从全局 map 里取记录
    const r = window.recordMap[id];
    if (!r) {
        console.error("未找到记录:", id);
        return;
    }

    if (action === "view") {
        showOverlay(r);

    } else if (action === "print") {
        if (!confirm("确认打印面单？")) return;
        printLabel(r);

    } else if (action === "ship") {
        if (!confirm("面单已经处理完成？")) return;
        shipProcessed(r)
            .then(() => {
                alert("出货申请处理成功！");
                row.remove();
            })
            .catch(err => {
                alert("出货申请处理失败，请稍后重试");
            });
    }
}

// ✅ 打开浮层并显示现有数据
// ✅ 打开浮层并显示现有数据
function openPackingOverlay(recordId) {
  const record = window.recordMap[recordId];
  if (!record) return alert("记录未找到");

  // ✅ 写入 recordId
  document.getElementById("recordId").value = recordId;

  // ✅ 兼容中英文字段名
  document.getElementById("barcode").value = record["产品条码"] ?? record.barcode ?? "";
  document.getElementById("cartons").value = record["箱数"] ?? record.cartons ?? "";
  document.getElementById("qty").value = record["每箱数量"] ?? record["QTY"] ?? record.qty ?? "";
  document.getElementById("weight").value = record["重量"] ?? record.weight ?? "";
  document.getElementById("spec").value = record["箱规"] ?? record.spec ?? "";
  document.getElementById("remark").value = record["备注"] ?? record.remark ?? "";

  // ✅ 显示浮层
  document.getElementById("packingOverlay").style.display = "block";
}

// ✅ 关闭浮层
function closePackingOverlay() {
  document.getElementById("packingOverlay").style.display = "none";
}

// ✅ 表单提交逻辑
document.getElementById("packingForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const recordId = document.getElementById("recordId").value;
  const fields = {
  "cartons": Number(document.getElementById("cartons").value),
  "qty": Number(document.getElementById("qty").value),
  "weight": Number(document.getElementById("weight").value),
  "spec": document.getElementById("spec").value.trim(),
  "remark": document.getElementById("remark").value.trim()
};

  const endpoint = "/ship_query/packing/update"; // 直接修改接口

  const resp = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recordId, fields })
  });

  const data = await resp.json();
  if (data.success) {
    alert("装箱数据已更新！");
    Object.assign(window.recordMap[recordId], fields);
    closePackingOverlay();
  } else {
    alert("更新失败：" + data.message);
  }
});