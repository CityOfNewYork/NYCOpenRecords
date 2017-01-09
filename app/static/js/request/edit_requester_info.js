$(function () {

    var requesterModal = $("#requesterModal");
    //  Switching to Modals
    requesterModal.on("shown.bs.modal", function () {
        $("#requesterInput").focus();
    });

    $("#agencyModal").on("shown.bs.modal", function () {
        $("#agencyInput").focus();
    });

    var telephone = $("#inputTelephone");
    var fax = $("#inputFax");
    var zipCode = $("#inputZip");
    var email = $("#inputEmail");
    var state = $("#inputState");
    var city = $("#inputCity");
    var addressOne = $("#inputAddressOne");

    var addressTwo = $("#inputAddressTwo");
    var title = $("#inputTitle");
    var organization = $("#inputOrganization");

    telephone.keypress(function (key) {
        if (key.charCode !== 0) {
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });

    fax.keypress(function (key) {
        if (key.charCode !== 0) {
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });

    telephone.mask("(999) 999-9999");
    fax.mask("(999) 999-9999");
    zipCode.mask("99999");

    var required = [
        telephone,
        email,
        fax,
        state,
        city,
        zipCode,
        addressOne
    ];

    var all = [
        telephone,
        email,
        fax,
        state,
        city,
        zipCode,
        addressOne,
        addressTwo,
        title,
        organization
    ];

    // Apply validators on modal open
    requesterModal.on("show.bs.modal", function () {
        for (var i = 0; i < required.length; i++) {
            required[i].attr("data-parsley-required", "");
            required[i].attr("data-parsley-required-message", "");
        }
        email.attr("data-parsley-maxlength", 254);
        zipCode.attr("data-parsley-length", "[5,5]");
        telephone.attr("data-parsley-length", "[14,14]");
        fax.attr("data-parsley-length", "[14,14]");

        zipCode.attr("data-parsley-length-message", "The Zipcode must be 5 digits long.");
        telephone.attr("data-parsley-length-message", "The phone number must be 10 digits long.");
        fax.attr("data-parsley-length-message", "The fax number must be 10 digits long.");
    });

    var errorMessage = $(".contact-form-error-message");

    $("#user-info").parsley().on("form:validate", function () {
        // Checks that at least one of the contact information fields is filled
        if (email.parsley().isValid() ||
            telephone.parsley().isValid() ||
            fax.parsley().isValid() || (
                // mailing address
                addressOne.parsley().isValid() &&
                state.parsley().isValid() &&
                zipCode.parsley().isValid() &&
                city.parsley().isValid()
            )
        ) {
            for (var i = 0; i < required.length; i++) {
                required[i].removeAttr("data-parsley-required");
            }
        }
        else {
            errorMessage.html(
                "At least one of the following need to be filled: " +
                "<strong>Email</strong>, <strong>Phone</strong>, <strong>Fax</strong>, " +
                "and/or <strong>Address</strong> (with <strong>City</strong>, " +
                "<strong>State</strong>, and <strong>Zipcode</strong>.)"
            );
        }
    });

    // Reset modal on close
    requesterModal.on("hidden.bs.modal", function () {
        var i;
        for (i = 0; i < all.length; i++) {
            all[i].val(all[i].attr("value"));
        }
        for (i = 0; i < required.length; i++) {
            $("#user-info").parsley().reset();
        }
        errorMessage.html("");
    });
});
