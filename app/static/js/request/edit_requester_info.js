"use strict";

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
    var selected_state_value = $("#inputState option:selected").val();
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
        title.attr("data-parsley-maxlength", 64);
        organization.attr("data-parsley-maxlength", 128);
        zipCode.attr("data-parsley-length", "[5,5]");
        telephone.attr("data-parsley-length", "[14,14]");
        fax.attr("data-parsley-length", "[14,14]");

        zipCode.attr("data-parsley-length-message", "The zipcode must be 5 digits long.");
        telephone.attr("data-parsley-length-message", "The phone number must be 10 digits long.");
        fax.attr("data-parsley-length-message", "The fax number must be 10 digits long.");

        characterCounter("#user-title-character-count", 64, title.val().length);
        characterCounter("#organization-character-count", 128, organization.val().length);
    });

    var errorMessage = $(".contact-form-error-message");

    $("#user-info").parsley().on("form:validate", function () {
        // Checks that at least one of the contact information fields is filled
        if (email.parsley().isValid() ||
            telephone.parsley().isValid() ||
            fax.parsley().isValid() ||
            (
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
                "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
                "At least one of the following needs to be filled: " +
                "<strong>Email</strong>, <strong>Phone</strong>, <strong>Fax</strong>, " +
                "and/or <strong>Address</strong> (with <strong>City</strong>, " +
                "<strong>State</strong>, and <strong>Zipcode</strong>.)"
            );
            errorMessage.focus();
        }
    });

    // Reset modal on close
    requesterModal.on("hidden.bs.modal", function () {
        var i;
        for (i = 0; i < all.length; i++) {
            all[i].val(all[i].attr("value"));
        }
        state.val(selected_state_value);
        for (i = 0; i < required.length; i++) {
            $("#user-info").parsley().reset();
        }
        errorMessage.html("");
    });

    title.keyup(function() {
        characterCounter("#user-title-character-count", 64, $(this).val().length)
    });

    organization.keyup(function() {
        characterCounter("#organization-character-count", 128, $(this).val().length)
    });
});
