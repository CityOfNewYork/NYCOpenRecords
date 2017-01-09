$(document).ready(function () {

    var name = $("#name");
    var email = $("#email");
    var subject = $("#subject");
    var message = $("#message");

    name.attr("data-parsley-required", "");
    email.attr("data-parsley-required", "");
    subject.attr("data-parsley-required", "");
    message.attr("data-parsley-required", "");

    name.attr('data-parsley-required-message', 'This information is required.');
    email.attr('data-parsley-required-message', 'This information is required.');
    subject.attr('data-parsley-required-message', 'This information is required.');
    message.attr('data-parsley-required-message', 'This information is required.');

    // Specify length requirement of certain fields
    name.attr('data-parsley-maxlength', 32);
    email.attr("data-parsley-maxlength", 254);
    subject.attr('data-parsley-maxlength', 90);
    message.attr('data-parsley-maxlength', 5000);

    $("#contact-info").parsley().on("form:validate", function () {
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
