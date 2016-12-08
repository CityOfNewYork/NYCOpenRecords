$(function () {

    var responses = null;
    var index = 0;
    var index_increment = 10;

    var request_id = $.trim($('#request-id').text());

    // get first set of responses on page load
    $.ajax({
        url: '/request/api/v1.0/responses',
        data: {
            start: 0,
            request_id: request_id,
            with_template: true
        },
        success: function (data) {
            responses = data.responses;
            if (responses.length > index_increment) {
                $('#responses-nav-buttons').show();
            }
            showResponses();
        },
        error: function (error) {
            console.log(error);
        }
    });

    function showResponses() {
        var response_list = $('#request-responses');
        response_list.empty();

        if (responses.length !== 0) {
            var index_incremented = index + index_increment;
            var end = responses.length < index_incremented ? responses.length : index_incremented;
            for (var i = index; i < end; i++) {
                response_list.append(responses[i].template);
                setEditResponseWorkflow(responses[i].id, responses[i].type);
                setDeleteResponseWorkflow(responses[i].id);
                if (responses[i].type === "files") {
                    bindFileUpload(
                        "#fileupload-update-" + responses[i].id,
                        request_id,
                        true,
                        "template-upload-update",
                        "template-download-update",
                        $("#response-modal-" + responses[i].id).find(
                            ".first").find(".response-modal-next")
                    );
                }
            }
            flask_moment_render_all();
        }
        else {
            response_list.text("None");
        }
    }

    function loadMoreResponses() {
        $.ajax({
            url: '/request/api/v1.0/responses',
            data: {
                start: responses.length,
                request_id: request_id,
                with_template: true
            },
            success: function (data) {
                responses = responses.concat(data.responses);
            },
            error: function (error) {
                console.log(error);
            }
        })
    }

    var nav_buttons = $('#responses-nav-buttons');

    // replaces currently displayed responses with previous 10 responses
    nav_buttons.find('.prev').click(function () {
        if (index !== 0) {
            index -= index_increment;
            showResponses();
        }
    });

    // replaces currently displayed responses with next 10 responses
    nav_buttons.find('.next').click(function () {
        index += index_increment;
        if (index == responses.length - index_increment) {
            loadMoreResponses();
        }
        if (responses.length < index) {
            index -= index_increment;
        }
        showResponses();
    });

    // TODO: DELETE 'updated' on modal close and reset / refresh page (wait until all responses ready)

    function setEditResponseWorkflow(response_id, response_type) {
        // FIXME: if response_type does not need email workflow, some of these elements won't be found!

        var responseModal = $("#response-modal-" + response_id);

        var first = responseModal.find(".first");
        var second = responseModal.find(".second");
        var third = responseModal.find(".third");

        var next1 = first.find(".response-modal-next");
        var next2 = second.find(".response-modal-next");
        var prev2 = second.find(".response-modal-prev");
        var prev3 = third.find(".response-modal-prev");

        var submitBtn = third.find(".response-modal-submit");

        // Initialize tinymce HTML editor
        tinymce.init({
            menubar: false,
            // sets tinymce to enable only on specific textareas classes
            mode: "specific_textareas",
            // selector for tinymce textarea classes is set to 'tinymce-area'
            editor_selector: "tinymce-area",
            elementpath: false,
            convert_urls: false,
            height: 180
        });

        switch (response_type) {
            case "files":  // TODO: constants?
                next1.click(function (e) {
                    // Validate fileupload form
                    first.find(".fileupload-form").parsley().validate();

                    // Do not proceed if file upload has not been completed
                    if (first.find(".template-download").length === 0 &&
                        first.find(".template-upload").length !== 0) {
                        first.find(".fileupload-error-messages").text(
                            "The file upload has not been completed").show();
                        e.preventDefault();
                        return false;
                    }

                    // Do not proceed if files with error are not removed
                    if (first.find(".upload-error").length > 0 ||
                        first.find(".error-post-fileupload").is(':visible')) {
                        first.find(".fileupload-error-messages").text(
                            "Files with Errors must be removed").show();
                        e.preventDefault();
                        return false;
                    }

                    if (first.find(".fileupload-form").parsley().isValid()) {
                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_edit_file.html",
                                type: "edit",
                                response_id: response_id,
                                title: first.find("input[name=title]").val(),
                                privacy: first.find("input[name=privacy]:checked").val(),
                                filename: first.find(".secured-name").length > 0 ? first.find(".secured-name").text() : null
                            },
                            success: function (data) {
                                if (data.error) {
                                    first.find(".fileupload-error-messages").text(data.error).show();
                                }
                                else {
                                    first.hide();
                                    second.show();
                                    first.find(".fileupload-error-messages").text(data.error).hide();
                                    tinyMCE.get("email-content-" + response_id).setContent(data.template);
                                }
                            }
                        });
                    }
                });

                next2.click(function () {
                    second.hide();
                    third.show();

                    tinyMCE.triggerSave();

                    var filename = first.find(".secured-name").text();
                    if (filename === "") {
                        filename = first.find(".uploaded-filename").text();
                    }
                    var privacy = first.find("input[name=privacy]:checked").val();

                    $.ajax({
                        url: "/response/email",
                        type: "POST",
                        data: {
                            request_id: request_id,
                            template_name: "email_edit_file.html",
                            type: "edit",
                            response_id: response_id,
                            title: first.find("input[name=title]").val(),
                            privacy: first.find("input[name=privacy]:checked").val(),
                            filename: first.find(".secured-name").length > 0 ? first.find(".secured-name").text() :
                                null,
                            confirmation: true,
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            third.find(".confirmation-header").text(data.header);
                            third.find(".email-summary").html(data.template);
                        }
                    });
                });

                prev2.click(function () {
                    first.find('.fileupload-error-messages').hide();
                    second.hide();
                    first.show();
                });

                prev3.click(function () {
                    third.hide();
                    second.show();
                });

                // SUBMIT!
                submitBtn.click(function () {
                    $(this).attr("disabled", true);
                    var form = first.find("form").serializeArray();
                    var email_content = second.find("#email-content-" + response_id).val();
                    form.push({ name: "email_content", value: email_content });
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form,
                        success: function () {
                            location.reload();
                        }
                    });
                });

                // Apply parsley required validation for title
                first.find("input[name=title]").attr("data-parsley-required", "");
                first.find("input[name=title]").attr("data-parsley-errors-container", ".title-error");

                break;

            case "notes":
                next1.click(function () {
                    first.find(".note-form").parsley().validate();

                    if (first.find(".note-form").parsley().isValid()) {
                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_edit_response.html",
                                type: "edit",
                                response_id: response_id,
                                content: first.find(".note-content").val(),
                                privacy: first.find("input[name=privacy]:checked").val(),
                            },
                            success: function (data) {
                                if (data.error) {
                                    first.find(".note-error-messages").text(
                                        data.error).show();
                                }
                                else {
                                    first.hide();
                                    second.show();
                                    first.find(".note-error-messages").text(
                                        data.error).hide();
                                    tinyMCE.get("email-content-" + response_id).setContent(data.template);
                                }
                            }
                        });
                    }
                });

                next2.click(function () {
                    second.hide();
                    third.show();

                    tinyMCE.triggerSave();

                    $.ajax({
                        url: "/response/email",
                        type: "POST",
                        data: {
                            request_id: request_id,
                            template_name: "email_edit_response.html",
                            type: "edit",
                            response_id: response_id,
                            content: first.find(".note-content").val(),
                            privacy: first.find("input[name=privacy]:checked").val(),
                            confirmation: true,
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            third.find(".confirmation-header").text(data.header);
                            third.find(".email-summary").html(data.template);
                        }
                    });
                });

                prev2.click(function () {
                    second.hide();
                    first.show();
                });

                prev3.click(function () {
                    third.hide();
                    second.show();
                });

                // SUBMIT!
                submitBtn.click(function () {
                    $(this).attr("disabled", true);
                    var form = first.find("form");
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form.serializeArray(),
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley data required validation to note content
                first.find('.note-content').attr("data-parsley-required", "");

                // Apply parsley max length validation to note content
                first.find('.note-content').attr("data-parsley-maxlength", "500");

                // Apply custom validation messages
                first.find('.note-content').attr("data-parsley-required-message",
                    "Note content must be provided");
                first.find('.note-content').attr("data-parsley-maxlength-message",
                    "Note content must be less than 500 characters");

                $(first.find(".note-content")).keyup(function () {
                    characterCounter(first.find(".note-content-character-count"), 500, $(this).val().length)
                });

                break;

            // TODO: call common function, stop copying code
            case "instructions":
                next1.click(function () {
                    first.find(".instruction-form").parsley().validate();

                    if (first.find(".instruction-form").parsley().isValid()) {
                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_edit_response.html",
                                type: "edit",
                                response_id: response_id,
                                content: first.find('.instruction-content').val(),
                                privacy: first.find("input[name=privacy]:checked").val(),
                            },
                            success: function (data) {
                                if (data.error) {
                                    first.find(".instruction-error-messages").text(
                                        data.error).show();
                                }
                                else {
                                    first.hide();
                                    second.show();
                                    first.find(".instruction-error-messages").text(
                                        data.error).hide();
                                    tinyMCE.get("email-content-" + response_id).setContent(data.template);
                                }
                            }
                        });
                    }
                });

                next2.click(function () {
                    second.hide();
                    third.show();

                    tinyMCE.triggerSave();

                    $.ajax({
                        url: "/response/email",
                        type: "POST",
                        data: {
                            request_id: request_id,
                            template_name: "email_edit_response.html",
                            type: "edit",
                            response_id: response_id,
                            content: first.find(".instruction-content").val(),
                            privacy: first.find("input[name=privacy]:checked").val(),
                            confirmation: true,
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            third.find(".confirmation-header").text(data.header);
                            third.find(".email-summary").html(data.template);
                        },
                        error: function (error) {
                            console.log(error);
                        }
                    });
                });

                prev2.click(function () {
                    second.hide();
                    first.show();
                });

                prev3.click(function () {
                    third.hide();
                    second.show();
                });

                // SUBMIT!
                submitBtn.click(function () {
                    $(this).attr("disabled", true);
                    var form = first.find("form");
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form.serializeArray(),
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley data required validation to instructions content
                first.find('.instruction-content').attr("data-parsley-required", "");

                // Apply parsley max length validation to instructions content
                first.find('.instruction-content').attr("data-parsley-maxlength", "500");

                // Apply custom validation messages
                first.find('.instruction-content').attr("data-parsley-required-message",
                    "Instruction content must be provided");
                first.find('.instruction-content').attr("data-parsley-maxlength-message",
                    "Instruction content must be less than 500 characters");

                $(first.find(".instruction-content")).keyup(function () {
                    characterCounter(first.find(".instruction-content-character-count"), 500, $(this).val().length)
                });

                break;

            case "links":
                first.find("input[name='url']").on('input', function () {
                    var urlVal = $(this).val();
                    first.find(".edit-link-href").attr("href", urlVal).text(urlVal);
                });

                next1.click(function () {
                    first.find(".link-form").parsley().validate();

                    if (first.find(".link-form").parsley().isValid()) {
                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_edit_response.html",
                                type: "edit",
                                response_id: response_id,
                                title: first.find(".title").val(),
                                url: first.find(".url").val(),
                                privacy: first.find("input[name=privacy]:checked").val(),
                            },
                            success: function (data) {
                                if (data.error) {
                                    first.find(".link-error-messages").text(
                                        data.error).show();
                                }
                                else {
                                    first.hide();
                                    second.show();
                                    first.find(".link-error-messages").text(
                                        data.error).hide();
                                    tinyMCE.get("email-content-" + response_id).setContent(data.template);
                                }
                            }
                        });
                    }
                });

                next2.click(function () {
                    second.hide();
                    third.show();

                    tinyMCE.triggerSave();

                    $.ajax({
                        url: "/response/email",
                        type: "POST",
                        data: {
                            request_id: request_id,
                            template_name: "email_edit_response.html",
                            type: "edit",
                            response_id: response_id,
                            title: first.find(".title").val(),
                            url: first.find(".url").val(),
                            privacy: first.find("input[name=privacy]:checked").val(),
                            confirmation: true,
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            third.find(".confirmation-header").text(data.header);
                            third.find(".email-summary").html(data.template);
                        }
                    });
                });

                prev2.click(function() {
                    second.hide();
                    first.show()
                });

                prev3.click(function () {
                    third.hide();
                    second.show();
                });

                // SUBMIT!
                submitBtn.click(function () {
                    $(this).attr("disabled", true);
                    var form = first.find("form");
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form.serializeArray(),
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley data required validation to link-form fields
                first.find(".title").attr("data-parsley-required", "");
                first.find(".url").attr("data-parsley-required", "");

                // Apply parsley max length validation to link-form fields
                first.find(".title").attr("data-parsley-maxlength", "90");
                first.find(".url").attr("data-parsley-required", "254");

                // Apply custom validation messages
                first.find('.title').attr('data-parsley-required-message', 'Link title must be provided.');
                first.find('.url').attr('data-parsley-required-message', 'URL link must be provided.');
                first.find('.title').attr('data-parsley-maxlength-message', 'Link title must be less than 90 characters.');
                first.find('.url').attr('data-parsley-maxlength-message', 'URL link must be less than 254 characters.');

                // Custom validator to validate strict url using regexUrlChecker
                first.find('.url').attr('data-parsley-urlstrict', '');

                // Set character counter for link title
                first.find('.title').keyup(function () {
                    characterCounter(first.find(".link-title-character-count"), 90, $(this).val().length)
                });

                // Set character counter for link url
                first.find('.url').keyup(function () {
                    characterCounter(first.find(".link-url-character-count"), 254, $(this).val().length)
                });

                break;

            default:
                break;
        }
    }

    function setDeleteResponseWorkflow(response_id) {
        var responseModal = $("#response-modal-" + response_id);
        var deleteSection = responseModal.find(".delete");
        var defaultSection = responseModal.find(".default");

        var deleteConfirmCheck = responseModal.find("input[name=delete-confirm-string]");
        var deleteConfirm = responseModal.find(".delete-confirm");

        deleteConfirmCheck.on('paste', function(e) {
            e.preventDefault();
        });

        var deleteConfirmString = "DELETE";
        deleteConfirmCheck.on("input", function() {
            if ($(this).val().toUpperCase() === deleteConfirmString) {
                deleteConfirm.attr("disabled", false);
            }
            else {
                deleteConfirm.attr("disabled", true);
            }
        });

        responseModal.find(".delete-select").click(function () {
            defaultSection.hide();
            deleteSection.show();
        });

        responseModal.find(".delete-cancel").click(function() {
            deleteSection.hide();
            defaultSection.show();

            deleteConfirmCheck.val('');
            deleteConfirm.attr("disabled", true);
        });

        responseModal.find(".delete-confirm").click(function() {
            deleteConfirm.attr("disabled", true);
            $.ajax({
                url: "/response/" + response_id,
                type: "PATCH",
                data: {
                    deleted: true,
                    confirmation: deleteConfirmCheck.val()
                },
                success: function() {
                    location.reload();
                },
                error: function(error) {
                    console.log(error)
                }
            })
        });
    }

});
