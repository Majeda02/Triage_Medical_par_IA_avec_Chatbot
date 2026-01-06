$(document).ready(function () {
  var table;
  const API_PATIENT = "/api/patient";

  window.__analysisCounts = {};

  function addPatient(data) {
    $.ajax({
      url: API_PATIENT,
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(data),
      success: function () {
        $('.modal.in').modal('hide');
        $.notify("Patient Added Successfully", { status: "success" });
        reloadTable();
      }
    });
  }

  function deletePatient(id) {
    swal({
      title: "Are you sure?",
      text: "You will not be able to recover this data",
      type: "warning",
      showCancelButton: true,
      confirmButtonColor: "#DD6B55",
      confirmButtonText: "Yes, delete it!",
      closeOnConfirm: false
    }, function () {
      $.ajax({
        url: API_PATIENT + "/" + id,
        method: "DELETE",
        success: function () {
          swal("Deleted!", "Patient has been deleted.", "success");
          reloadTable();
        }
      });
    });
  }

  function updatePatient(data, id) {
    $.ajax({
      url: API_PATIENT + "/" + id,
      method: "PUT",
      contentType: "application/json",
      data: JSON.stringify(data),
      success: function () {
        $('.modal.in').modal('hide');
        $.notify("Patient Updated Successfully", { status: "success" });
        reloadTable();
      }
    });
  }

  function reloadTable() {
    if (table) table.destroy();
    $('#datatable4 tbody').empty();
    getPatient();
  }

 
  function openAnalyseModal(patId, patName){
    $("#analysePatientName").text(patName);
    $("#analysePatientId").text(patId);

    $("#analyseTable tbody").empty();
    $("#analyseEmpty").hide();

    $.ajax({
      url: "/api/patient/" + patId + "/triage-analyses",
      method: "GET",
      dataType: "json",
      success: function(rows){
        if (!rows || rows.length === 0){
          $("#analyseEmpty").show();
          $("#analyseModal").modal("show");
          return;
        }
        window.__currentAnalysesRows = rows || [];
        window.__currentPatientName = patName || "";
        window.__currentPatientId = patId;


        rows.forEach(function(r){
          const date = r.created_at || "";
          const label = r.label || "";
          const pred = r.pred || "";

          let probaTxt = "";
          if (r.proba_json){
            try{
              const obj = (typeof r.proba_json === "string") ? JSON.parse(r.proba_json) : r.proba_json;
              probaTxt = Object.keys(obj).map(k => `${k}: ${(obj[k]*100).toFixed(1)}%`).join("<br>");
            } catch(e){ probaTxt = ""; }
          }

          let usedHtml = "";
          if (r.payload_json){
            try{
          const obj2 = (typeof r.payload_json === "string") ? JSON.parse(r.payload_json) : r.payload_json;

              usedHtml = Object.keys(obj2).map(k => {
                const v = (obj2[k] === null || obj2[k] === undefined) ? "" : String(obj2[k]);
                return `<div><b>${k}</b>: ${v}</div>`;
              }).join("");
            } catch(e){ usedHtml = ""; }
          }
        



          $("#analyseTable tbody").append(`
            <tr>
                <td>${date}</td>
                <td><b>${label}</b></td>
                <td><div class="used-box">${usedHtml || ""}</div></td>
              </tr>
            `);

        });

        $("#analyseModal").modal("show");
      },
      error: function(xhr){
          console.error("Historique analyses error:", xhr.status, xhr.responseText);
          alert("Erreur historique analyses: " + xhr.status + "\n" + (xhr.responseText || ""));
    }

    });
  }

  function getPatient() {
    $.ajax({
      url: API_PATIENT,
      method: "GET",
      dataType: "json",
      success: function (patients) {

        console.log("PATIENT API RESPONSE:", patients);

        const ids = (patients || []).map(p => p.pat_id).filter(Boolean);

        if (ids.length === 0) {
          window.__analysisCounts = {};
          buildTable(patients);
          return;
        }

        $.ajax({
          url: "/api/triage/analysis-counts?ids=" + encodeURIComponent(ids.join(",")),
          method: "GET",
          dataType: "json",
          success: function(counts){
            window.__analysisCounts = counts || {};
            buildTable(patients);
          },
          error: function(xhr){
            console.warn("analysis-counts failed:", xhr.status, xhr.responseText);
            window.__analysisCounts = {};
            buildTable(patients);
          }
        });
      },
      error: function(xhr){
        console.error("GET /api/patient failed:", xhr.status, xhr.responseText);
        alert("API patient error: " + xhr.status);
      }
    });
  }

  function buildTable(patients){
    table = $('#datatable4').DataTable({
      destroy: true,
      paging: true,
      ordering: true,
      info: true,
      data: patients,
      columns: [
  { data: 'pat_first_name' },
  { data: 'pat_last_name' },
  { data: 'pat_insurance_no' },
  { data: 'pat_address' },
  { data: 'pat_ph_no' },

  {
    data: null,
    render: function (data, type, row) {
      const id = row.pat_id;
      const name = `${row.pat_first_name || ""} ${row.pat_last_name || ""}`.trim();
      const n = window.__analysisCounts[String(id)] ? Number(window.__analysisCounts[String(id)]) : 0;

      let html = `
        <button class="btn btn-info btn-sm openChat" data-id="${id}">
          Analyse
        </button>
      `;

      if (n > 0) {
        html += `
          <button class="btn btn-success btn-sm openAnalyseHistory"
                  data-id="${id}"
                  data-name="${name}">
            Analyses (${n})
          </button>
        `;
      }

      return `<div class="analyse-actions">${html}</div>`;
    }
  },

  {
    data: null,
    render: function () {
      return `
        <div class="action-actions">
          <button class="btn btn-action btn-action-edit btn-edit" type="button">
            <i class="fa fa-pencil"></i> Edit
          </button>
          <button class="btn btn-action btn-action-del delete-btn" type="button">
            <i class="fa fa-trash"></i> Delete
          </button>
        </div>
      `;
    }
  }
]

    });

    $("#btnExportPdf").off("click").on("click", function () {
  const rows = window.__currentAnalysesRows || [];
  const patId = window.__currentPatientId || $("#analysePatientId").text();
  const patName = window.__currentPatientName || $("#analysePatientName").text();

  if (!rows.length) {
    alert("Aucune analyse à exporter.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "mm", "a4");

  doc.setFontSize(16);
  doc.text("Rapport - Historique des analyses", 14, 16);

  doc.setFontSize(11);
  doc.text(`Patient: ${patName} (ID: ${patId})`, 14, 24);
  doc.text(`Date d'export: ${new Date().toLocaleString()}`, 14, 30);

  const body = rows.map(r => {
    const date = r.created_at || "";
    const statut = r.label || ""; 

    let usedTxt = "";
    if (r.payload_json) {
  const obj = (typeof r.payload_json === "string") ? JSON.parse(r.payload_json) : r.payload_json;
  usedTxt = Object.keys(obj).map(k => `${k}: ${obj[k]}`).join("\n");
}


    return [date, statut, usedTxt];
  });

  doc.autoTable({
    startY: 36,
    head: [["Date", "Patient status", "Analyse"]],
    body: body,
    styles: { fontSize: 9, cellPadding: 2, overflow: "linebreak" },
    headStyles: { fontSize: 10 },
    columnStyles: {
      0: { cellWidth: 35 },
      1: { cellWidth: 35 },
      2: { cellWidth: 110 }
    }
  });

  const safeName = (patName || "patient").replace(/[\\/:*?"<>|]/g, "_").trim();
  doc.save(`rapport_triage_${safeName}_id${patId}.pdf`);
});


    $('#datatable4 tbody').off('click', '.openChat').on('click', '.openChat', function () {
      const id = $(this).data("id");
      window.location.href = "chatbot.html?pat_id=" + encodeURIComponent(id);
    });

    $('#datatable4 tbody').off('click', '.openAnalyseHistory').on('click', '.openAnalyseHistory', function () {
      const id = $(this).data("id");
      const name = $(this).data("name") || "";
      openAnalyseModal(id, name);
    });

    $('#datatable4 tbody').off('click', '.delete-btn').on('click', '.delete-btn', function () {
      var row = table.row($(this).parents('tr')).data();
      deletePatient(row.pat_id);
    });

    $('#datatable4 tbody').off('click', '.btn-edit').on('click', '.btn-edit', function () {
      var row = table.row($(this).parents('tr')).data();
      $('#myModal').modal('show').one('shown.bs.modal', function () {
        for (var key in row) $("[name=" + key + "]").val(row[key]);

        $("#savethepatient").off("click").on("click", function () {
          var instance = $('#detailform').parsley();
          instance.validate();
          if (instance.isValid()) {
            var jsondata = $('#detailform').serializeJSON();
            updatePatient(jsondata, row.pat_id);
          }
        });
      });
    });

    $("#btnNewAnalyse").off("click").on("click", function(){
      const id = $("#analysePatientId").text();
      if (id && id !== "—") {
        window.location.href = "chatbot.html?pat_id=" + encodeURIComponent(id);
      }
    });

    $("#btnExportCsv").off("click").on("click", function(){
  const id = $("#analysePatientId").text();
  if (id && id !== "—") {
    window.location.href = "/api/patient/" + encodeURIComponent(id) + "/triage-export.csv";
  }
});
  }

  $("#addpatient").off("click").on("click", function () {
    $('#detailform input,textarea').val("");
    $('#myModal').modal('show').one('shown.bs.modal', function () {
      $("#savethepatient").off("click").on("click", function () {
        var instance = $('#detailform').parsley();
        instance.validate();
        if (instance.isValid()) {
          var jsondata = $('#detailform').serializeJSON();
          addPatient(jsondata);
        }
      });
    });
  });

  getPatient();
});
