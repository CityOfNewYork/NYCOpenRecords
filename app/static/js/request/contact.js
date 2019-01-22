"use strict";

$(document).ready(function () {

    var name = $("#name");
    var email = $("#email");
    var subject = $("#subject");
    var message = $("#message");

    name.attr("data-parsley-required", "");
    email.attr("data-parsley-required", "");
    subject.attr("data-parsley-required", "");
    message.attr("data-parsley-required", "");

    // Custom validation messages
    name.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, a name is required.</strong> Please type in your name.");
    email.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, an email is required.</strong> Please type in your email.");
    email.attr("data-parsley-type-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this value should be an email.</strong> Please type in a valid email.");
    subject.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, a subject is required.</strong> Please type in a subject name.");
    message.attr("data-parsley-required-message",
        "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, a message is required.</strong> Please type in a message.");

    // Specify length requirement of certain fields
    name.attr('data-parsley-maxlength', 32);
    email.attr("data-parsley-maxlength", 254);
    subject.attr('data-parsley-maxlength', 90);
    message.attr('data-parsley-maxlength', 5000);

    $("#contact-info").parsley().on("form:validated", function () {
        if (name.parsley().isValid() === false) {
            $(window).scrollTop($("label[for=name]").offset().top);
        }
        else if (email.parsley().isValid() === false) {
            $(window).scrollTop($("label[for=email]").offset().top);
        }
        else if (subject.parsley().isValid() === false) {
            $(window).scrollTop($("label[for=subject]").offset().top);
        }
        else {
            $(window).scrollTop($("label[for=message]").offset().top);
        }
        // Add tab index to any error messages
        $(".parsley-required").each(function () {
            $(this).attr("tabindex", 0);
        });
        $(".parsley-type").each(function () {
            $(this).attr("tabindex", 0);
        });
    });
    
    // Set character counter for note content
    name.keyup(function() {
        characterCounter("#name-character-count", 32, $(this).val().length)
    });
    
    subject.keyup(function() {
        characterCounter("#subject-character-count", 90, $(this).val().length)
    });
    
    message.keyup(function() {
        characterCounter("#message-character-count", 5000, $(this).val().length)
    });
});
