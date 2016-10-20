//  Switching to Modals
$('#requesterModal').on('shown.bs.modal', function () {
  $('#requesterInput').focus()
});

$('#agencyModal').on('shown.bs.modal', function () {
  $('#agencyInput').focus()
});

$('#inputTelephone').mask('(999) 999-9999');

