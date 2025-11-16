function openModal(id, date, requestor, office, unit, description, status, personnel, materials, reports) {
  document.getElementById("modal-date").textContent = date;
  document.getElementById("modal-requestor").textContent = requestor;
  document.getElementById("modal-office").textContent = office;
  document.getElementById("modal-unit").textContent = unit;
  document.getElementById("modal-description").textContent = description;
  document.getElementById("modal-status").textContent = status;
  document.getElementById("modal-personnel").textContent = personnel || "Unassigned";
  document.getElementById("modal-materials").textContent = materials || "No materials assigned";
  document.getElementById("modal-reports").innerHTML = reports || "No reports submitted";

  const approveForm = document.getElementById("approveForm");

  if (approveForm) {
      approveForm.action = `/gso_requests/approve/${id}/`;

      // Show Approve only when Pending AND personnel assigned
      if (status === "Pending" && personnel && personnel.trim() !== "") {
          approveForm.style.display = "block";
      } else {
          approveForm.style.display = "none";
      }
  }

  new bootstrap.Modal(document.getElementById("requestModal")).show();
}
