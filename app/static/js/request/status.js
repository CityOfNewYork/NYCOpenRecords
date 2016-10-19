// $(document).ready(function () {
//     $('[data-toggle="popover"]').popover();
// });
//  $(function() {
//      // Enables popover #1
//      $("[data-toggle=popover]").popover();
//
//      // Enables popover #2
//      $("#example-popover-2").popover({
//          html: true,
//          content: function () {
//              return $("#example-popover-2-content").html();
//          },
//          title: function () {
//              return $("#example-popover-2-title").html();
//          }
//      });
//      // Popover Function
//  }

//  Switching to Modals
$('#requesterModal').on('shown.bs.modal', function () {
  $('#requesterInput').focus()
});

$('#agencyModal').on('shown.bs.modal', function () {
  $('#agencyInput').focus()
});

$('#inputTelephone').mask('(999) 999-9999');

