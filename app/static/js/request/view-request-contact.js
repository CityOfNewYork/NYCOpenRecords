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

    firstName.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>First name is required.</strong> Please type in your first name.");
    lastName.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Last name is required.</strong> Please type in your last name.");
    email.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>An email name is required.</strong> Please type in your email.");
    email.attr("data-parsley-type-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>This value should be an email.</strong> Please type in a valid email.");
    subject.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>A subject is required.</strong> Please type in a subject name.");
    message.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>A message is required.</strong> Please type in a message.");

    firstName.attr('data-parsley-maxlength', 32);
    lastName.attr('data-parsley-maxlength', 64);
    email.attr("data-parsley-maxlength", 254);
    message.attr('data-parsley-maxlength', 5000);

    $("#contact-form").parsley().on("form:validated", function () {
        // Add tab index to any error messages
        $(".parsley-required").each(function () {
            $(this).attr("tabindex", 0);
        });
        $(".parsley-type").each(function () {
            $(this).attr("tabindex", 0);
        });
    });

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
