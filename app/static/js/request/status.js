//  Switching to Modals
$('#requesterModal').on('shown.bs.modal', function () {
    $('#requesterInput').focus()
});

$('#agencyModal').on('shown.bs.modal', function () {
    $('#agencyInput').focus()
});

$('#inputTelephone').mask('(999) 999-9999');
$('#inputFax').mask('(999) 999-9999');
$('#inputZip').mask('99999');

// Looping through required fields and applying a data-parsley-required attribute to them
var required_fields = ['inputEmail', 'inputTelephone', 'inputAddressOne', 'inputAddressTwo', 'inputCity', 'inputZip', 'inputState', 'inputOrganization', 'inputFax'];
for (i = 0; i < required_fields.length; i++) {
    $('#' + required_fields[i]).attr('data-parsley-required', '')
}

//Apply parsley validation styles
$('#inputZip').attr('data-parsley-length', '[5,5]');

//Apply custom validation messages


//Disable default error messages for email, phone, fax, and address


//






//Activating
$('#user-info').parsley().validate();

