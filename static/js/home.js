$(document).ready(function () {

  $.ajax({
    url: "/api/common",
    method: "GET",
    dataType: "json",
    cache: false,
    success: function (response) {

      console.log("COMMON RESPONSE 👉", response);

      $("#patientcount").text(response.patient || 0);
      $("#doctorcount").text(response.doctor || 0);
      $("#appointmentcount").text(response.appointment || 0);
    },
    error: function (xhr) {
      console.error("COMMON API ERROR:", xhr.status, xhr.responseText);

      $("#patientcount").text("—");
      $("#doctorcount").text("—");
      $("#appointmentcount").text("—");
    }
  });

});
