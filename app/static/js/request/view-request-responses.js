$(function () {

    var responses = null;
    var index = 0;
    var index_increment = 10;

    var request_id = $('#request-id').text();

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

        var index_incremented = index + index_increment;
        var end = responses.length < index_incremented ? responses.length : index_incremented;
        for (var i = index; i < end; i++) {
            response_list.append(responses[i].template);
            setEditResponseWorkflow(responses[i].id, responses[i].type);
            if (responses[i].type === "file") {
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
        if (index != 0) {
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

    // TODO: remove after QA
    $('#request-responses').on('click', '.tmp-save-changes', function () {
        var form = $(this).parents('.modal-body').children('form');
        var response_id = $(this).parents('.modal-content').children('.response-id').text();
        var data = form.serializeArray();
        data.push({
            name: "email_content",
            value: "Why hello there..."
        });
        $.ajax({
            url: "/response/" + response_id,
            type: "PUT",
            data: data,
            success: function (response) {
                console.log(response);
            }
        });
    });

    // TODO: DELETE updated on modal close and reset (or just refresh page)

    function setEditResponseWorkflow(response_id, response_type) {
        var response_modal = $("#response-modal-" + response_id);

        var first = response_modal.find('.first');
        var second = response_modal.find('.second');
        var third = response_modal.find('.third');

        var next1 = first.find('.response-modal-next');
        var next2 = second.find('.response-modal-next');
        var prev2 = second.find('.response-modal-prev');
        var prev3 = third.find('.response-modal-prev');

        // Initialize tinymce HTML editor
        tinymce.init({
            // sets tinymce to enable only on specific textareas classes
            mode: "specific_textareas",
            // selector for tinymce textarea classes is set to 'tinymce-area'
            editor_selector: "tinymce-area",
            elementpath: false,
            height: 180
        });

        switch (response_type) {
            case "file":
                next1.click(function (e) {
                    // Validate fileupload form
                    first.find(".fileupload-form").parsley().validate();

                    // Do not proceed if file upload has not been completed
                    if (first.find('.template-download').length === 0 &&
                        first.find('.template-upload').length != 0) {
                        first.find(".fileupload-error-messages").text(
                            "The file upload has not been completed").show();
                        e.preventDefault();
                        return false;
                    }

                    // Do not proceed if files with error are not removed
                    if (first.find('.upload-error').length > 0 ||
                        first.find(".error-post-fileupload").is(':visible')) {
                        first.find('.fileupload-error-messages').text(
                            "Files with Errors must be removed").show();
                        e.preventDefault();
                        return false;
                    }

                    if (first.find(".fileupload-form").parsley().isValid()) {
                        first.hide();
                        second.show();

                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_response_file.html",
                                type: "file"
                            },
                            success: function (data) {
                                // Data should be html template page.
                                tinyMCE.get("email-content-" + response_id).setContent(data);
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

                    var files = [{
                        "filename": filename,
                        "privacy": privacy
                    }];

                    $.ajax({
                        url: "/response/email",
                        type: "POST",
                        data: {
                            request_id: request_id,
                            template_name: "email_response_file.html",
                            type: "file",
                            files: JSON.stringify(files),
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            // Data should be html template page.
                            third.find(".email-summary").html(data);
                        },
                        error: function (error) {
                            console.log(error);
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
                third.find(".response-modal-submit").click(function() {
                    var form = first.find("form");
                    var data = form.serializeArray();
                    data.push({
                        name: "email_content",
                        value: third.find(".email-summary:hidden").html()
                    });
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PUT",
                        data: data,
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley required validation for title
                first.find("input[name=title]").attr('data-parsley-required', '');
                first.find("input[name=title]").attr('data-parsley-errors-container', '.title-error');

                break;

            case "note":
                next1.click(function () {
                    // Validate fileupload form
                    first.find(".note-form").parsley().validate();

                    if (first.find(".note-form").parsley().isValid()) {
                        first.hide();
                        second.show();

                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                response_id: response_id,
                                template_name: "email_edit_response.html",
                                type: "edit",
                                content: first.find('#note-content').val(),
                                privacy: first.find("input[name=privacy]:checked").val()
                            },
                            success: function (data) {
                                // Data should be html template page.
                                tinyMCE.get("email-content-" + response_id).setContent(data);
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
                            type: "note",
                            note: JSON.stringify({
                                content: first.find('#note-content').val(),
                                privacy: first.find("input[name=privacy]:checked").val()
                            }),
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            // Data should be html template page.
                            third.find(".email-summary").html(data);
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
                third.find(".response-modal-submit").click(function() {
                    var form = first.find("form");
                    var data = form.serializeArray();
                    data.push({
                        name: "email_content",
                        value: third.find(".email-summary:hidden").html()
                    });
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PUT",
                        data: data,
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley data required validation to note title and url
                first.find('#note-content').attr('data-parsley-required', '');

                // Apply parsley max length validation to note title and url
                first.find('#note-content').attr('data-parsley-maxlength', '500');

                // Apply custom validation messages
                first.find('#note-content').attr('data-parsley-required-message', 'Note content must be provided');
                first.find('#note-content').attr('data-parsley-maxlength-message', 'Note content must be less than 500 characters');

                break;
            default:
                break;
        }
    }

});
