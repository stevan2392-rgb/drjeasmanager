async function fetchJSON(url, options = {}) {
  const response = await fetch(
    url,
    Object.assign({ headers: { "Content-Type": "application/json" } }, options)
  );
  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = data.error || data.message || message;
    } catch (_error) {
      const text = await response.text();
      if (text) message = text;
    }
    throw new Error(message);
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function money(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

let productsCache = [];

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await refreshAll();
});

function bindEvents() {
  document.getElementById("btnAddProduct").addEventListener("click", saveProduct);
  document.getElementById("btnCancelEditProduct").addEventListener("click", resetProductForm);
  document.getElementById("btnAdjust").addEventListener("click", adjustInventory);
  document.getElementById("btnAddPurchaseItem").addEventListener("click", () => addItemRow("purchaseItems", "purchase"));
  document.getElementById("btnSavePurchase").addEventListener("click", savePurchase);
  document.getElementById("btnAddRemissionItem").addEventListener("click", () => addItemRow("remissionItems", "sale"));
  document.getElementById("btnSaveRemission").addEventListener("click", saveRemission);
  document.getElementById("btnAddInvoiceItem").addEventListener("click", () => addItemRow("invoiceItems", "sale"));
  document.getElementById("btnSaveInvoice").addEventListener("click", saveInvoice);
  document.getElementById("btnDownloadSalesReport").addEventListener("click", downloadSalesReport);
}

async function refreshAll() {
  await refreshProducts();
  await refreshAlerts();
}

async function refreshProducts() {
  productsCache = await fetchJSON("/api/products");

  const selectAdjust = document.getElementById("adjustProduct");
  const tableBody = document.querySelector("#productTable tbody");
  selectAdjust.innerHTML = "";
  tableBody.innerHTML = "";

  productsCache.forEach((product) => {
    const option = document.createElement("option");
    option.value = product.id;
    option.textContent = `${product.sku} - ${product.name}`;
    selectAdjust.appendChild(option);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${product.sku}</td>
      <td>${product.name}</td>
      <td>${money(product.price)}</td>
      <td>${product.supplier_name || "Sin proveedor"}</td>
      <td>${product.total_sold || 0}</td>
      <td>${product.current_stock}</td>
      <td>${product.low_stock_threshold}</td>
      <td class="text-center">
        <button class="btn btn-sm btn-outline-primary me-1" onclick="startEditProduct(${product.id})">Editar</button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteProduct(${product.id})">Eliminar</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

async function refreshAlerts() {
  const lowStock = await fetchJSON("/api/alerts/low-stock");
  const lowStockList = document.getElementById("lowStockList");
  lowStockList.innerHTML = "";

  if (lowStock.length === 0) {
    lowStockList.innerHTML = '<li class="list-group-item">Sin alertas por ahora.</li>';
  } else {
    lowStock.forEach((product) => {
      const li = document.createElement("li");
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      li.innerHTML = `<span>${product.sku} - <strong>${product.name}</strong></span><span>Stock: ${product.current_stock}</span>`;
      lowStockList.appendChild(li);
    });
  }

  const maintenance = await fetchJSON("/api/alerts/maintenance");
  const maintenanceList = document.getElementById("maintenanceList");
  maintenanceList.innerHTML = "";

  if (maintenance.length === 0) {
    maintenanceList.innerHTML = '<li class="list-group-item">Nada pendiente en las pr&oacute;ximas 2 semanas.</li>';
    return;
  }

  maintenance.forEach((reminder) => {
    const li = document.createElement("li");
    const customer = reminder.customer || {};
    li.className = "list-group-item d-flex justify-content-between align-items-center";
    li.innerHTML = `
      <div>
        <div class="fw-semibold">${customer.name || "Cliente sin nombre"}</div>
        <small class="text-muted">${reminder.due_date || ""} ${reminder.notes || ""}</small>
      </div>
      <button type="button" class="btn btn-sm btn-success" onclick="completeMaintenance(${reminder.id})">Hecho</button>
    `;
    maintenanceList.appendChild(li);
  });
}

async function completeMaintenance(reminderId) {
  if (!confirm("Confirma que este mantenimiento ya fue realizado.")) return;
  await fetchJSON("/api/alerts/maintenance/complete", {
    method: "POST",
    body: JSON.stringify({ id: reminderId }),
  });
  await refreshAlerts();
}

function productPayloadFromForm() {
  return {
    name: document.getElementById("prodName").value.trim(),
    sku: document.getElementById("prodSKU").value.trim(),
    price: parseFloat(document.getElementById("prodPrice").value || "0"),
    current_stock: parseInt(document.getElementById("prodStock").value || "0", 10),
    low_stock_threshold: parseInt(document.getElementById("prodLow").value || "0", 10),
    supplier_name: document.getElementById("prodSupplier").value.trim(),
    reason: "edicion manual",
  };
}

async function saveProduct() {
  const editingId = document.getElementById("editingProductId").value;
  const payload = productPayloadFromForm();
  try {
    const url = editingId ? `/api/products/${editingId}` : "/api/products";
    const method = editingId ? "PUT" : "POST";
    await fetchJSON(url, { method, body: JSON.stringify(payload) });
    resetProductForm();
    await refreshAll();
  } catch (error) {
    alert(`No se pudo guardar el producto: ${error.message}`);
  }
}

function startEditProduct(productId) {
  const product = productsCache.find((item) => item.id === productId);
  if (!product) return;
  document.getElementById("editingProductId").value = product.id;
  document.getElementById("prodName").value = product.name;
  document.getElementById("prodSKU").value = product.sku;
  document.getElementById("prodPrice").value = product.price;
  document.getElementById("prodStock").value = product.current_stock;
  document.getElementById("prodLow").value = product.low_stock_threshold;
  document.getElementById("prodSupplier").value = product.supplier_name || "";
  document.getElementById("btnAddProduct").textContent = "Actualizar";
  document.getElementById("editProductActions").classList.remove("d-none");
  document.getElementById("prodName").focus();
}

function resetProductForm() {
  document.getElementById("editingProductId").value = "";
  document.getElementById("prodName").value = "";
  document.getElementById("prodSKU").value = "";
  document.getElementById("prodPrice").value = "";
  document.getElementById("prodStock").value = "0";
  document.getElementById("prodLow").value = "5";
  document.getElementById("prodSupplier").value = "";
  document.getElementById("btnAddProduct").textContent = "Guardar";
  document.getElementById("editProductActions").classList.add("d-none");
}

async function deleteProduct(productId) {
  if (!confirm("Seguro que deseas eliminar este producto?")) return;
  try {
    const result = await fetchJSON(`/api/products/${productId}`, { method: "DELETE" });
    alert(result.message || "Producto eliminado");
    await refreshAll();
  } catch (error) {
    alert(`No se pudo eliminar: ${error.message}`);
  }
}

async function adjustInventory() {
  const payload = {
    product_id: parseInt(document.getElementById("adjustProduct").value || "0", 10),
    quantity: parseInt(document.getElementById("adjustQty").value || "0", 10),
    reason: document.getElementById("adjustReason").value.trim() || "ajuste manual",
  };
  if (!payload.product_id || !payload.quantity) {
    alert("Selecciona producto y cantidad.");
    return;
  }
  try {
    await fetchJSON("/api/inventory/adjust", { method: "POST", body: JSON.stringify(payload) });
    document.getElementById("adjustQty").value = "1";
    document.getElementById("adjustReason").value = "";
    await refreshAll();
  } catch (error) {
    alert(`No se pudo ajustar el inventario: ${error.message}`);
  }
}

function addItemRow(tableId, type) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  const tr = document.createElement("tr");
  const options = productsCache
    .map((product) => `<option value="${product.id}">${product.sku} - ${product.name}</option>`)
    .join("");

  tr.innerHTML = `
    <td><select class="form-select item-product">${options}</select></td>
    <td><input type="number" class="form-control item-qty" value="1" min="1"></td>
    <td><input type="number" class="form-control item-price" value="0" min="0" step="0.01"></td>
    <td><button type="button" class="btn btn-sm btn-outline-danger">Eliminar</button></td>
  `;

  tr.querySelector("button").addEventListener("click", () => tr.remove());

  const select = tr.querySelector(".item-product");
  const priceInput = tr.querySelector(".item-price");
  const applyProductDefaults = () => {
    const product = productsCache.find((item) => item.id === parseInt(select.value, 10));
    if (!product) return;
    priceInput.value = product.price;
    if (type === "purchase" && !document.getElementById("supName").value.trim() && product.supplier_name) {
      document.getElementById("supName").value = product.supplier_name;
    }
  };
  select.addEventListener("change", applyProductDefaults);
  tbody.appendChild(tr);
  applyProductDefaults();
}

function collectRows(tableId) {
  return Array.from(document.querySelectorAll(`#${tableId} tbody tr`)).map((row) => ({
    product_id: parseInt(row.querySelector(".item-product").value, 10),
    quantity: parseInt(row.querySelector(".item-qty").value || "0", 10),
    unit_price: parseFloat(row.querySelector(".item-price").value || "0"),
    unit_cost: parseFloat(row.querySelector(".item-price").value || "0"),
  }));
}

async function savePurchase() {
  const items = collectRows("purchaseItems");
  if (items.length === 0) {
    alert("Agrega al menos un item.");
    return;
  }
  try {
    const result = await fetchJSON("/api/purchases", {
      method: "POST",
      body: JSON.stringify({
        supplier: {
          name: document.getElementById("supName").value.trim(),
          phone: document.getElementById("supPhone").value.trim(),
          email: document.getElementById("supEmail").value.trim(),
          address: document.getElementById("supAddress").value.trim(),
        },
        items,
        notes: document.getElementById("purchaseNotes").value.trim(),
      }),
    });
    document.getElementById("purchaseResult").innerHTML = `<div class="alert alert-success">Compra <strong>${result.code}</strong> guardada por ${money(result.total)}.</div>`;
    document.querySelector("#purchaseItems tbody").innerHTML = "";
    document.getElementById("purchaseNotes").value = "";
    await refreshAll();
  } catch (error) {
    alert(`No se pudo guardar la compra: ${error.message}`);
  }
}

function collectCustomer(prefix) {
  return {
    name: document.getElementById(`${prefix}Name`).value.trim(),
    document_number: document.getElementById(`${prefix}Doc`).value.trim(),
    phone: document.getElementById(`${prefix}Phone`).value.trim(),
    email: document.getElementById(`${prefix}Email`).value.trim(),
    address: document.getElementById(`${prefix}Addr`).value.trim(),
  };
}

async function saveRemission() {
  const items = collectRows("remissionItems");
  if (items.length === 0) {
    alert("Agrega al menos un item.");
    return;
  }
  try {
    const result = await fetchJSON("/api/remissions", {
      method: "POST",
      body: JSON.stringify({
        customer: collectCustomer("rem"),
        items,
        payment_method: document.getElementById("remPaymentMethod").value,
        maintenance_days: parseInt(document.getElementById("remMaintenanceDays").value || "0", 10),
        paid_amount: parseFloat(document.getElementById("remPaidAmount").value || "0"),
        notes: document.getElementById("remNotes").value.trim(),
      }),
    });
    document.getElementById("remissionResult").innerHTML = `<div class="alert alert-success">Remisi&oacute;n <strong>${result.number}</strong> creada por ${money(result.total)}. <a href="/remission/${result.id}" target="_blank">Ver</a></div>`;
    document.querySelector("#remissionItems tbody").innerHTML = "";
    document.getElementById("remMaintenanceDays").value = "";
    document.getElementById("remPaidAmount").value = "0";
    document.getElementById("remNotes").value = "";
    await refreshAll();
  } catch (error) {
    alert(`No se pudo crear la remisión: ${error.message}`);
  }
}

async function saveInvoice() {
  const items = collectRows("invoiceItems");
  if (items.length === 0) {
    alert("Agrega al menos un item.");
    return;
  }
  try {
    const result = await fetchJSON("/api/invoices", {
      method: "POST",
      body: JSON.stringify({
        customer: collectCustomer("inv"),
        items,
        payment_method: document.getElementById("invPaymentMethod").value,
        maintenance_days: parseInt(document.getElementById("invMaintenanceDays").value || "0", 10),
        notes: document.getElementById("invNotes").value.trim(),
      }),
    });
    document.getElementById("invoiceResult").innerHTML = `<div class="alert alert-success">Factura <strong>${result.number}</strong> creada por ${money(result.total)}. <a href="/invoice/${result.id}" target="_blank">Ver</a></div>`;
    document.querySelector("#invoiceItems tbody").innerHTML = "";
    document.getElementById("invMaintenanceDays").value = "";
    document.getElementById("invNotes").value = "";
    await refreshAll();
  } catch (error) {
    alert(`No se pudo crear la factura: ${error.message}`);
  }
}

function downloadSalesReport() {
  window.open("/api/reports/sales?format=csv", "_blank");
}
