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

    name.attr('data-parsley-maxlength', 96);
    email.attr("data-parsley-maxlength", 254);
    subject.attr('data-parsley-maxlength', 90);
    message.attr('data-parsley-maxlength', 5000);

    $("#contact-form").parsley();

    name.keyup(function() {
        characterCounter("#name-character-count", 96, $(this).val().length)
    });

    message.keyup(function() {
        characterCounter("#message-character-count", 5000, $(this).val().length)
    });
});
