// apple-query.js / apply-query.js
// 说明：保持 ship-query.html 界面与交互不变；
// 本文件仅把原先通过 postMessage 的查询/打印，改为直接调用后端 /ship-query/api/* 接口。

(function () {
  const shipmentTableBody = document.querySelector("#shipmentTable tbody");
  const paginationDiv = document.getElementById("pagination");
  const searchBtn = document.getElementById("searchBtn");
  const searchInput = document.getElementById("searchInput");

  let currentPage = 1;
  const pageSize = 10;
  let currentRecord = null; // 覆盖层中正在查看/打印的记录

  async function queryShipments({ page = 1, pageSize = 20, search = "" }) {
    const params = new URLSearchParams({
      page: String(page),
      pageSize: String(pageSize),
    });
    if (search && search.trim() !== "") {
      params.append("search", search.trim());
    }

    const resp = await fetch(`/ship_query/api/shipments?${params.toString()}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`查询失败: ${resp.status} ${txt}`);
    }
    return await resp.json();
  }

  function renderTable(result) {
    shipmentTableBody.innerHTML = "";

    if (!result.records || result.records.length === 0) {
      shipmentTableBody.innerHTML = `<tr><td colspan="6">没有数据</td></tr>`;
      paginationDiv.innerHTML = "";
      return;
    }

    result.records.forEach((r) => {
      const changeFiles = (r.changeLabels && r.changeLabels.length > 0)
        ? r.changeLabels.map(file => `<a href="${file.url}" target="_blank">${file.name}</a>`).join("<br>")
        : "";

      const fbaFiles = (r.fbaLabels && r.fbaLabels.length > 0)
        ? r.fbaLabels.map(file => `<a href="${file.url}" target="_blank">${file.name}</a>`).join("<br>")
        : "";

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${r.barcode || ""}</td>
        <td>${r.cartons || ""}</td>
        <td>${r.qty || ""}</td>
        <td>${r.createdAt ? new Date(r.createdAt).toLocaleString('en-US', { hour12: false }) : ""}</td>
        <td>${changeFiles}</td>
        <td>${fbaFiles}</td>
        <td>
          <a href="javascript:void(0)" class="view-label">查看</a>  &nbsp;
          <a href="javascript:void(0)" class="print-link">打印</a>
          <a href="javascript:void(0)" class="ship-processed">处理完成</a>

        </td>
      `;
      shipmentTableBody.appendChild(row);

      // 查看
      const viewLink = row.querySelector(".view-label");
      viewLink.addEventListener("click", () => showOverlay(r));

      // 打印
      const printLink = row.querySelector(".print-link");
      printLink.addEventListener("click", async () => {
        if (!confirm("确认打印面单？")) return;
        try {
          await printLabel(r);
          console.log("[Renderer] 打印任务提交成功");
        } catch (err) {
          console.error("[Renderer] 打印失败:", err);
          alert("打印失败，请稍后重试");
        }
      });

      // 把申请标识成已经处理完成
      const processElement = row.querySelector(".ship-processed");
      processElement.addEventListener("click", async () => {
        if (!confirm("面单已经处理完成？")) return;
        try {
          await shipProcessed(r);
          alert("出货申请处理成功！");
          row.remove();
          console.log("[Renderer] 出货申请处理成功");
        } catch (err) {
          console.error("[Renderer] 出货申请处理失败:", err);
          alert("出货申请处理失败，请稍后重试");
        }
      });
    });

    // 分页按钮
    paginationDiv.innerHTML = "";
    for (let i = 1; i <= (result.totalPages || 1); i++) {
      const btn = document.createElement("button");
      btn.textContent = i;
      if (i === result.page) btn.disabled = true;
      btn.addEventListener("click", () => {
        currentPage = i;
        loadData();
      });
      paginationDiv.appendChild(btn);
    }
  }

  async function loadData() {
    const search = searchInput.value.trim();
    const result = await queryShipments({ page: currentPage, pageSize, search });
    renderTable(result);
  }

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
    const payload = { record: record || currentRecord };
    if (!payload.record) {
      alert("没有可打印的记录");
      return;
    }

    const resp = await fetch("/ship_query/api/print", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
    // 允许 ship-query.html 里直接调用 printLabel()（无参），则使用当前记录
    const payload = { record: record || currentRecord };
    if (!payload.record) {
      alert("没有可处理的记录");
      return;
    }

    const resp = await fetch("/ship_query/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok || data.error) {
      throw new Error(data.error || `处理申请的接口返回错误 (${resp.status})`);
    }

    return data;
  };

  // 事件绑定
  searchBtn.addEventListener("click", () => {
    currentPage = 1;
    loadData();
  });

  // 初次加载
  document.addEventListener("DOMContentLoaded", () => {
    loadData().catch(err => console.error(err));
  });

  // 立即执行一次（有些环境不触发 DOMContentLoaded）
  loadData().catch(err => console.error(err));
})();