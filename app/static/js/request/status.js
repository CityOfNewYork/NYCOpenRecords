$(function () {

    //  Switching to Modals
    $("#requesterModal").on('shown.bs.modal', function () {
        $('#requesterInput').focus()
    });

    $("#agencyModal").on('shown.bs.modal', function () {
        $('#agencyInput').focus()
    });

    var telephone = $("#inputTelephone");
    var fax = $("#inputFax");
    var zip = $("#inputZip");
    var email = $("#inputEmail");
    var state = $("#inputState");
    var city = $("#inputCity");
    var address_one = $("#inputAddressOne");
    var address_two = $("#inputAddressTwo");
    var organization = $("#inputOrganization");

    telephone.keypress(function (key) {
        if (key.charCode != 0) {
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });

    fax.keypress(function (key) {
        if (key.charCode != 0) {
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });


    telephone.mask("(999) 999-9999");
    fax.mask("(999) 999-9999");
    zip.mask("99999");

    // Apply validators
    var required = [
        telephone,
        email,
        fax,
        state,
        city,
        zip,
        address_one
    ];
    for (var i = 0; i < required.length; i++) {
        required[i].attr('data-parsley-required', '')
    }
    zip.attr('data-parsley-length', '[5,5]');
    telephone.attr('data-parsley-length', '[14,14]');
    fax.attr('data-parsley-length', '[14,14]');

    // Apply custom validation messages
    fax.attr('data-parsley-length-message', 'The fax number must be 10 digits long.');
    telephone.attr('data-parsley-length-message', 'The phone number must be 10 digits long.');
    zip.attr('data-parsley-length-message', 'The Zipcode must be 5 digits long.');
    address_one.attr('data-parsley-length-message', 'Must be a valid address');
    // Disable default error messages for email, phone, fax, and address
    telephone.attr('data-parsley-required-message', '');
    fax.attr('data-parsley-required-message', '');
    address_one.attr('data-parsley-required-message', '');
    city.attr('data-parsley-required-message', '');
    email.attr('data-parsley-required-message', '');
    zip.attr('data-parsley-required-message', '');

    // ON VALIDATE
    $('#user-info').parsley().subscribe('parsley:form:validate', function () {
        // Checks that at least one of the contact information fields is filled
        if (email.parsley().isValid() ||
            telephone.parsley().isValid() ||
            fax.parsley().isValid() ||
            (address_one.parsley().isValid() &&  // mailing address
            state.parsley().isValid() &&
            zip.parsley().isValid() &&
            city.parsley().isValid())
        ) {
            city.removeAttr('data-parsley-required');
            state.removeAttr('data-parsley-required');
            zip.removeAttr('data-parsley-required');
            telephone.removeAttr('data-parsley-required');
            fax.removeAttr('data-parsley-required');
            address_one.removeAttr('data-parsley-required');
            email.removeAttr('data-parsley-required');
        }
        else {
            $('.contact-form-error-message').html(
                "At least one of the following need to be filled: " +
                "<strong>Email</strong>, <strong>Phone</strong>, <strong>Fax</strong>, " +
                "and/or <strong>Address</strong> (with <strong>City</strong>, " +
                "<strong>State</strong>, and <strong>Zipcode</strong>.)"
            );
        }
    });

});
