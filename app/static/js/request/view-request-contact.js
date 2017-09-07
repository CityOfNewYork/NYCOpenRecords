"use strict";

$(document).ready(function () {

    var firstName = $("#first-name");
    var lastName = $("#last-name");
    var email = $("#email");
    var subject = $("#subject");
    var message = $("#message");

    firstName.attr("data-parsley-required", "");
    lastName.attr("data-parsley-required", "");
    email.attr("data-parsley-required", "");
    subject.attr("data-parsley-required", "");
    message.attr("data-parsley-required", "");

    firstName.attr('data-parsley-required-message', 'This information is required.');
    lastName.attr('data-parsley-required-message', 'This information is required.');
    email.attr('data-parsley-required-message', 'This information is required.');
    subject.attr('data-parsley-required-message', 'This information is required.');
    message.attr('data-parsley-required-message', 'This information is required.');

    firstName.attr('data-parsley-maxlength', 32);
    lastName.attr('data-parsley-maxlength', 64);
    email.attr("data-parsley-maxlength", 254);
    message.attr('data-parsley-maxlength', 5000);

    $("#contact-form").parsley();

    firstName.keyup(function() {
        characterCounter("#first-name-character-count", 32, $(this).val().length)
    });

    lastName.keyup(function() {
        characterCounter("#last-name-character-count", 64, $(this).val().length)
    });

    message.keyup(function() {
        characterCounter("#message-character-count", 5000, $(this).val().length)
    });
});
