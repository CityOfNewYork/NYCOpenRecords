/**
 * Created by atan on 9/22/16.
 */

"use strict";

$(document).ready(function () {

    // popover when selecting the title and description
    $("[data-toggle='popover']").popover();

    var phone = $("#phone"),
        fax = $("#fax"),
        zip = $("#zipcode"),
        email = $("#email"),
        title = $("#title"),
        organization = $("#organization"),
        address1 = $("#address-line-1"),
        city = $("#city"),
        state = $("#state");

    // Prevent user from entering a non numeric value into phone and fax field
    phone.keypress(function(key) {
        if(key.charCode < 48 || key.charCode > 57)
            key.preventDefault();
    });
    fax.keypress(function(key) {
        if(key.charCode < 48 || key.charCode > 57)
            key.preventDefault();
    });

    // jQuery mask plugin to format fields
    phone.mask("(999) 999-9999");
    fax.mask("(999) 999-9999");
    zip.mask("99999");

    // Loop through required fields and apply a data-parsley-required attribute to them
    var requiredFields = [phone, fax, address1, city, zip, email, state];
    for (var i = 0 ; i < requiredFields.length ; i++) {
        requiredFields[i].attr("data-parsley-required", "");
        requiredFields[i].attr("data-parsley-required-message", "");
    }

    // Specify length requirement of certain fields
    phone.attr("data-parsley-length","[14,14]");
    fax.attr("data-parsley-length","[14,14]");
    zip.attr("data-parsley-length", "[5,5]");
    email.attr("data-parsley-maxlength", 254);
    title.attr("data-parsley-maxlength", 64);
    organization.attr("data-parsley-maxlength", 128);

    // Custom length validation messages
    fax.attr("data-parsley-length-message", "The fax number must be 10 digits.");
    phone.attr("data-parsley-length-message", "The phone number must be 10 digits.");
    zip.attr("data-parsley-length-message", "The zipcode must be 5 digits.");

    // set character counter
    characterCounter("#title-character-count", 64, title.val().length);
    title.keyup(function() {
        characterCounter("#title-character-count", 64, title.val().length);
    });
    characterCounter("#organization-character-count", 128, organization.val().length);
    organization.keyup(function () {
        characterCounter("#organization-character-count", 128, organization.val().length);
    });

    $("#request-form").parsley().on("form:validate", function () {
        // Checks that at least one of the contact information fields is filled
        if (email.parsley().isValid() ||
            phone.parsley().isValid() ||
            fax.parsley().isValid() ||
            (
                // mailing address
                address1.parsley().isValid() &&
                state.parsley().isValid() &&
                zip.parsley().isValid() &&
                city.parsley().isValid()
            )
        ) {
            for (var i = 0; i < requiredFields.length; i++) {
                requiredFields[i].removeAttr("data-parsley-required");
            }
        }
        else {
            $(".contact-form-error-message").html(
                "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
                "At least one of the following needs to be filled: " +
                "<strong>Notification Email</strong>, <strong>Phone</strong>, " +
                "<strong>Fax</strong>, and/or <strong>Address</strong> " +
                "(with <strong>City</strong>, <strong>State</strong>, and <strong>Zip code</strong>.)"
            );
            $(".contact-form-error-message").focus();
        }
    });

});
