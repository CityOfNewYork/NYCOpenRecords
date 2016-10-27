//  Switching to Modals
$('#requesterModal').on('shown.bs.modal', function () {
    $('#requesterInput').focus()
});

$('#agencyModal').on('shown.bs.modal', function () {
    $('#agencyInput').focus()
});

$(document).ready(function() {
    $("#inputTelephone").keydown(function (e) {
        // Allow: backspace, delete, tab, escape, enter and .
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 13, 110, 190]) !== -1 ||
             // Allow: Ctrl+A, Command+A
            (e.keyCode === 65 && (e.ctrlKey === true || e.metaKey === true)) ||
             // Allow: home, end, left, right, down, up
            (e.keyCode >= 35 && e.keyCode <= 40)) {
                 // let it happen, don't do anything
                 return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
});

$(document).ready(function() {
    $("#inputFax").keydown(function (e) {
        // Allow: backspace, delete, tab, escape, enter and .
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 13, 110, 190]) !== -1 ||
             // Allow: Ctrl+A, Command+A
            (e.keyCode === 65 && (e.ctrlKey === true || e.metaKey === true)) ||
             // Allow: home, end, left, right, down, up
            (e.keyCode >= 35 && e.keyCode <= 40)) {
                 // let it happen, don't do anything
                 return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
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
$('#inputTelephone').attr('data-parsley-length', '[14,14]');
$('#inputFax').attr('data-parsley-length', '[14,14]');

//Apply custom validation messages
$('#inputFax').attr('data-parsley-length-message', 'The fax number must be 10 digits long.');
$('#inputTelephone').attr('data-parsley-length-message', 'The phone number must be 10 digits long.');
$('#inputZip').attr('data-parsley-length-message', 'The Zipcode must be 5 digits long.');
$('#inputAddressOne').attr('data-parsley-length-message', 'The Zipcode must be 5 digits long.');

//Disable default error messages for email, phone, fax, and address
$('#inputTelephone').attr('data-parsley-required-message', '');
$('#inputFax').attr('data-parsley-required-message', '');
$('#inputAddressOne').attr('data-parsley-required-message', '');
$('#inputCity').attr('data-parsley-required-message', '');
$('#inputEmail').attr('data-parsley-required-message', '');
$('#inputZip').attr('data-parsley-required-message', '');

//Checks that at least one of the contact information fields is filled in addition to the rest of the form
if ($('#inputEmail').parsley().isValid() ||
    $('#inputPhone').parsley().isValid() ||
    $('#inputFax').parsley().isValid() ||
    $('#inputAddressOne').parsley().isValid() ||
    $('#inputState').parsley().isValid() &&
    $('#inputZip').parsley().isValid() &&
    $('#inputCity').parsley().isValid()
)
{
    $('#inputCity').removeAttr('data-parsley-required');
    $('#inputState').removeAttr('data-parsley-required');
    $('#inputZip').removeAttr('data-parsley-required');
    $('#inputTelephone').removeAttr('data-parsley-required');
    $('#inputFax').removeAttr('data-parsley-required');
    $('#inputAddressTwo').removeAttr('data-parsley-required');
    $('#inputAddressOne').removeAttr('data-parsley-required');
    $('#inputOrganization').removeAttr('data-parsley-required');
    $('#inputEmail').removeAttr('data-parsley-required');
}
else
{
    //If none of the fields are valid, then produce an error message for them
    $('.contact-form-error-message').html("At least one of the following need to be filled: Email, Phone, Fax, and/or Address (with City, State, and Zipcode");
    $('#inputFax').attr('data-parsley-required', '');
    $('#inputTelephone').attr('data-parsley-required', '');
    $('#inputZip').attr('data-parsley-required', '');
    $('#inputCity').attr('data-parsley-required', '');
    $('#inputState').attr('data-parsley-required', '');
    $('#inputEmail').attr('data-parsley-required', '');
}


//Activating
$('#user-info').parsley().validate();
