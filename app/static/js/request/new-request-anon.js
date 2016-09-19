/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {

    // jQuery mask plugin to format fields
    $('#phone').mask("999-999-9999");
    $('#zipcode').mask("99999");

    // Apply parsley validation styles to the input forms for a new request.

    // Loop through required fields and apply a data-parsley-required attribute to them
    var required_fields = ['request-title','request-description', 'request-agency', 'first-name','last-name','email',
        'phone','fax','address-line-1', 'city', 'zipcode'];
    for (i = 0 ; i < required_fields.length ; i++){
        $('#' + required_fields[i]).attr('data-parsley-required','');
    }

    // Specify length requirement of certain fields
    $('#request-title').attr('data-parsley-maxlength', 90);
    $('#request-description').attr('data-parsley-maxlength', 5000);
    $('#phone').attr('data-parsley-length','[10,10]');
    $('#zipcode').attr('data-parsley-length', '[5,5]');

    // Custom Validation Messages
    $('#phone').attr('data-parsley-minlength-message', 'Must be a 10 digit phone number');

    // Disable default error messages for email,phone,fax,address so custom one can be used instead.
    $('#phone').attr('data-parsley-required-message', '');
    $('#fax').attr('data-parsley-required-message', '');
    $('#address-line-1').attr('data-parsley-required-message', '');
    $('#city').attr('data-parsley-required-message','');
    $('#email').attr('data-parsley-required-message', '');
    $('#zipcode').attr('data-parsley-required-message','');

    // Contact information validation
    $('#email').attr('data-parsley-type', 'email');
    // Checks that at least one form of contact was filled out in addition to the rest of the form.
    $('#request-form').parsley().subscribe('parsley:form:validate', function () {
        if ($('#address-line-1').parsley().isValid()){
                $('#city').attr('data-parsley-required','');
                $('#state').attr('data-parsley-required','');
                $('#zipcode').attr('data-parsley-required','');
            }
        if ($('#email').parsley().isValid() ||
            $('#phone').parsley().isValid() ||
            $('#fax').parsley().isValid() ||
            ($('#address-line-1').parsley().isValid() && $('#state').parsley().isValid() && $('#zipcode').parsley().isValid() && $('#city').parsley().isValid())
            &&
            ($('#request-agency').parsley().isValid() &&
            $('#request-title').parsley().isValid() &&
            $('#request-description').parsley().isValid() &&
            $('#first-name').parsley().isValid() &&
            $('#last-name').parsley().isValid())
        ) {
            // If at least one of the fields are validated then removed their requirement
            $('#city').removeAttr('data-parsley-required');
            $('#state').removeAttr('data-parsley-required');
            $('#zipcode').removeAttr('data-parsley-required');
            $('#phone').removeAttr('data-parsley-required');
            $('#fax').removeAttr('data-parsley-required');
            $('#address-line-1').removeAttr('data-parsley-required');
            $('#email').removeAttr('data-parsley-required');
        }
        else {
            // If none of the fields are valid then produce an error message and apply required fields.
            $('.contact-form-error-message').html("*At least one of the following must be filled out: Email, Phone, Fax, and Address (with City, State, and Zipcode)");
            $('#fax').attr('data-parsley-required', '');
            $('#phone').attr('data-parsley-required', '');
            $('#address-line-1').attr('data-parsley-required', '');
            $('#email').attr('data-parsley-required', '');
        }
    });

});
