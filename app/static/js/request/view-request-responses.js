"use strict";

$(function () {

    var responses = null;
    var index = 0;
    var indexIncrement = 5;
    var total = 0;
    var alphaNumericChars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

    var request_id = $.trim($('#request-id').text());
    var navButtons = $('#responses-nav-buttons');
    var prevButton = navButtons.find(".prev");
    var nextButton = navButtons.find(".next");
    var requestResponses = $("#request-responses");

    $.blockUI.defaults.css.border = "";
    $.blockUI.defaults.css.backgroundColor = "";
    $.blockUI.defaults.overlayCSS.backgroundColor = "gray";
    requestResponses.block({
        message: "<div class=\"col-sm-12 loading-container\"><div class=\"loading-spinner\">" +
        "<span class=\"sr-only\">Loading responses...</span></div></div>"
    });

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
            total = data.total;
            if (responses.length > indexIncrement) {
                navButtons.show();
                prevButton.attr("disabled", true);
            }
            $("#request-responses-section").unblock();
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
            var indexIncremented = index + indexIncrement;
            var end = responses.length < indexIncremented ? responses.length : indexIncremented;
            for (var i = index; i < end; i++) {
                response_list.append(responses[i].template);
                setEditResponseWorkflow(responses[i].id, responses[i].type);
                setDeleteResponseWorkflow(responses[i].id);
                if (responses[i].type === "files") {
                    bindFileUpload(
                        "#fileupload-update-" + responses[i].id,
                        request_id,
                        '',
                        true,
                        responses[i].id,
                        "template-upload-update",
                        "template-download-update",
                        $("#response-modal-" + responses[i].id).find(
                            ".first").find(".response-modal-next")
                    );
                }
            }
            flask_moment_render_all();
            $("#request-responses-section").unblock();
        }
        else {
            response_list.html("<div class=\"center-text\">" +
                "<br/><br/>There are no responses available for this request.</div>");
        }
    }


    function loadMoreResponses() {
        $("#request-responses").html("<div class='loading'></div>");
        $("#request-responses-section").block({
            message: "<div class=\"col-sm-12 loading-container\"><div class=\"loading-spinner\">" +
            "<span class=\"sr-only\">Loading responses...</span></div></div>"
        });
        $.ajax({
            url: '/request/api/v1.0/responses',
            data: {
                start: responses.length,
                request_id: request_id,
                with_template: true
            },
            success: function (data) {
                responses = responses.concat(data.responses);
                if (index + indexIncrement >= responses.length) {
                    nextButton.attr("disabled", true);
                }
            },
            error: function (error) {
                console.log(error);
            },
            complete: showResponses
        })
    }

    function getRandomString(length, chars) {
        var string = '';
        for (var i = length; i > 0; --i) string += chars[Math.floor(Math.random() * chars.length)];
        return string;
    }

    // replaces currently displayed responses with previous 10 responses
    prevButton.click(function () {
        nextButton.attr("disabled", false);
        if (index !== 0) {
            index -= indexIncrement;
            if (index === 0) {
                $(this).attr("disabled", true);
            }
            showResponses();
        }
    });

    // replaces currently displayed responses with next 10 responses
    nextButton.click(function () {
        prevButton.attr("disabled", false);
        index += indexIncrement;
        if (index === responses.length) {
            loadMoreResponses();
        }
        else if (index + indexIncrement >= total) {
            nextButton.attr("disabled", true);
            showResponses();
        }
        else {
            showResponses();
        }
    });

    // TODO: DELETE 'updated' on modal close and reset / refresh page (wait until all responses ready)

    function setEditResponseWorkflow(response_id, response_type) {

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
            mode: 'specific_textareas',
            // selector for tinymce textarea classes is set to 'tinymce-area'
            editor_selector: 'tinymce-area',
            elementpath: false,
            convert_urls: false,
            height: 300,
            plugins: ['noneditable', 'preventdelete', 'lists'],
            toolbar: ['undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent add_check'],
            setup: function (editor) {
                editor.ui.registry.addButton('add_check', {
                    text: 'Add  ✔',
                    onAction: function () {
                        editor.insertContent('&nbsp;&#10004;&nbsp;');
                    }
                });
            }
        });

        switch (response_type) {
            case "files":  // TODO: constants?
                first.find(".fileupload-form input").on("keyup keypress", function (e) {  // TODO: global function
                    if (e.keyCode === 13) {
                        e.preventDefault();
                    }
                });

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
                            filename: first.find(".secured-name").length > 0 ? first.find(".secured-name").text() : null,
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
                    var randomString = getRandomString(32, alphaNumericChars);
                    var emailSummaryHidden = third.find(".email-summary-hidden");
                    emailSummaryHidden.html(third.find(".email-summary").html());
                    emailSummaryHidden.find(".file-links").html(randomString);
                    first.find("input[name='replace-string']").val(randomString);
                    first.find("input[name='email_content']").val(emailSummaryHidden.html());
                    var form = first.find("form").serializeArray();
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
                    tinyMCE.triggerSave();

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
                                privacy: first.find("input[name=privacy]:checked").val()
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

                tinymce.init({
                    menubar: false,
                    // sets tinymce to enable only on specific textareas classes
                    mode: 'specific_textareas',
                    // selector for tinymce textarea classes is set to 'tinymce-area'
                    editor_selector: 'tinymce-edit-note-content',
                    elementpath: false,
                    convert_urls: false,
                    height: 300,
                    plugins: ['noneditable', 'preventdelete', 'lists'],
                    toolbar: ['undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent add_check'],
                    forced_root_block: '',
                    setup: function (editor) {
                        editor.ui.registry.addButton('add_check', {
                            text: 'Add  ✔',
                            onAction: function () {
                                editor.insertContent('&nbsp;&#10004;&nbsp;');
                            }
                        });

                        editor.on('keyup', function () {
                            let currentLength = tinyMCE.get(editor.id).getContent({format: 'text'}).trim().length;
                            characterCounter('#character-counter-' + editor.id, 5000, currentLength);
                            if (currentLength > 5000) {
                                $('#response-' + response_id + '-next-1').prop('disabled', true);
                                $('#' + editor.id + '-maxlength-error').show();
                            } else {
                                $('#response-' + response_id + '-next-1').prop('disabled', false);
                                $('#' + editor.id + '-maxlength-error').hide();
                            }
                        });
                    }
                });

                // Apply parsley data required validation to note content
                first.find('.note-content').attr("data-parsley-required", "");

                // Apply custom validation messages
                first.find('.note-content').attr("data-parsley-required-message",
                    "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
                    "<strong>Error, note content is required.</strong> Please type in a message.");

                // Check the ID to make sure the tinymce field exists before setting the character counter
                if ($('#note-' + response_id).length) {
                    characterCounter('#character-counter-note-' + response_id, 5000, tinyMCE.get('note-' + response_id).getContent({format: 'text'}).trim().length);
                }

                break;

            // TODO: call common function, stop copying code
            case "instructions":
                next1.click(function () {
                    tinyMCE.triggerSave();

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

                tinymce.init({
                    menubar: false,
                    // sets tinymce to enable only on specific textareas classes
                    mode: 'specific_textareas',
                    // selector for tinymce textarea classes is set to 'tinymce-area'
                    editor_selector: 'tinymce-edit-instruction-content',
                    elementpath: false,
                    convert_urls: false,
                    height: 300,
                    plugins: ['noneditable', 'preventdelete', 'lists'],
                    toolbar: ['undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent add_check'],
                    forced_root_block: '',
                    setup: function (editor) {
                        editor.ui.registry.addButton('add_check', {
                            text: 'Add  ✔',
                            onAction: function () {
                                editor.insertContent('&nbsp;&#10004;&nbsp;');
                            }
                        });

                        editor.on('keyup', function () {
                            let currentLength = tinyMCE.get(editor.id).getContent({format: 'text'}).trim().length;
                            characterCounter('#character-counter-' + editor.id, 500, currentLength, 20);
                            if (currentLength > 500) {
                                $('#response-' + response_id + '-next-1').prop('disabled', true);
                                $('#' + editor.id + '-maxlength-error').show();
                            } else {
                                $('#response-' + response_id + '-next-1').prop('disabled', false);
                                $('#' + editor.id + '-maxlength-error').hide();
                            }
                        });
                    }
                });

                // Apply parsley data required validation to instructions content
                first.find('.instruction-content').attr("data-parsley-required", "");
                first.find('.instruction-content').attr("data-parsley-minlength", 20);

                // Apply custom validation messages
                first.find('.instruction-content').attr("data-parsley-required-message",
                    "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
                    "<strong>Error, Offline Instructions are required.</strong> Please type in some instructions.");

                first.find('.instruction-content').attr("data-parsley-minlength-message",
                    "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
                    "<strong>Error, Offline Instructions must be at least 20 characters.</strong>");

                // Check the ID to make sure the tinymce field exists before setting the character counter
                if ($('#instruction-' + response_id).length) {
                    characterCounter('#character-counter-instruction-' + response_id, 500, tinyMCE.get('instruction-' + response_id).getContent({format: 'text'}).trim().length, 20);
                }

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

                prev2.click(function () {
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
        var editFileTitle = "#edit-file-title-" + response_id;
        var editFileTitleCharacterCounter = "#edit-file-title-character-counter-" + response_id;
        $(editFileTitle).keyup(function () {
            characterCounter(editFileTitleCharacterCounter, 250, $(this).val().length)
        });
    }

    function setDeleteResponseWorkflow(response_id) {
        var responseModal = $("#response-modal-" + response_id);
        var deleteSection = responseModal.find(".delete");
        var defaultSection = responseModal.find(".default");

        var deleteConfirmCheck = responseModal.find("input[name=delete-confirm-string]");
        var deleteConfirm = responseModal.find(".delete-confirm");

        deleteConfirmCheck.on('paste', function (e) {
            e.preventDefault();
        });

        var deleteConfirmString = "DELETE";
        deleteConfirmCheck.on("input", function () {
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

        responseModal.find(".delete-cancel").click(function () {
            deleteSection.hide();
            defaultSection.show();

            deleteConfirmCheck.val('');
            deleteConfirm.attr("disabled", true);
        });

        responseModal.find(".delete-confirm").click(function () {
            deleteConfirm.attr("disabled", true);
            $.ajax({
                url: "/response/" + response_id,
                type: "PATCH",
                data: {
                    deleted: true,
                    confirmation: deleteConfirmCheck.val()
                },
                success: function () {
                    location.reload();
                },
                error: function (error) {
                    console.log(error)
                }
            })
        });
    }

});
