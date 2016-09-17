/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {
    // Datepicker for date request was received when creating a new request
    $(".dtpick").datepicker({
        dateFormat: "yy-mm-dd"
    });
    // $('#request-form').parsley().subcribe('parsley:form:validate', function(formInstance){
    // })
    // Apply parsley validation styles to the input forms for a new request.
    document.getElementById('request-title').setAttribute('data-parsley-required', '');
    document.getElementById('request-title').setAttribute('data-parsley-maxlength', 90);
    document.getElementById('request-agency').setAttribute('data-parsley-required', '');
    document.getElementById('request-description').setAttribute('data-parsley-required', '');
    document.getElementById('request-description').setAttribute('data-parsley-maxlength', 5000);
    document.getElementById('first-name').setAttribute('data-parsley-required', '');
    document.getElementById('last-name').setAttribute('data-parsley-required', '');
    // Contact information validation
    document.getElementById('email').setAttribute('data-parsley-errors-messages-disabled', '');
    document.getElementById('email').setAttribute('data-parsley-type', 'email');
    document.getElementById('phone').setAttribute('data-parsley-errors-messages-disabled', '');
    document.getElementById('fax').setAttribute('data-parsley-errors-messages-disabled', '');
    document.getElementById('zipcode').setAttribute('data-parsley-length', '[5,5]');
    document.getElementById('address-line-1').setAttribute('data-parsley-errors-messages-disabled', '');
    document.getElementById('fax').setAttribute('data-parsley-required', '');
    document.getElementById('phone').setAttribute('data-parsley-required', '');
    document.getElementById('address-line-1').setAttribute('data-parsley-required', '');
    document.getElementById('email').setAttribute('data-parsley-required', '');
    // var formInstance = $('#request-form').parsley();
    window.Parsley.addValidator('')
    $('#request-form').parsley().subscribe('parsley:form:validate', function (formInstance) {
        if ($('#email').parsley().isValid() ||
            $('#phone').parsley().isValid() ||
            $('#fax').parsley().isValid() ||
            $('#address-line-1').parsley().isValid()) {
            $('#phone').removeAttr('data-parsley-required').parsley().destroy();
            $('#fax').removeAttr('data-parsley-required').parsley().destroy();
            $('#address-line-1').removeAttr('data-parsley-required').parsley().destroy();
            $('#email').removeAttr('data-parsley-required').parsley().destroy();
        }
        else {
            $('.contact-form-error-message').html("*At least one of the following must be filled out: Email, Phone, Fax, and Address");
            document.getElementById('fax').setAttribute('data-parsley-required', '');
            document.getElementById('phone').setAttribute('data-parsley-required', '');
            document.getElementById('address-line-1').setAttribute('data-parsley-required', '');
            document.getElementById('email').setAttribute('data-parsley-required', '');
        }
    });
});
