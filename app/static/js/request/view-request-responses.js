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

        // Initialize tinymce HTML editor
        tinymce.init({
            menubar: false,
            // sets tinymce to enable only on specific textareas classes
            mode: "specific_textareas",
            // selector for tinymce textarea classes is set to 'tinymce-area'
            editor_selector: "tinymce-area",
            elementpath: false,
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
                        first.hide();
                        second.show();

                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_response_file.html",
                                type: "files"
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
                            type: "files",
                            files: JSON.stringify(files),
                            email_content: $("#email-content-" + response_id).val()
                        },
                        success: function (data) {
                            // Data should be html template page.
                            third.find(".email-summary").html(data);
                            // TODO: data should also return email confirmation header
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
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form.serializeArray(), // TODO: remove hidden email summaries
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
                        first.hide();
                        second.show();

                        $.ajax({
                            url: "/response/email",
                            type: "POST",
                            data: {
                                request_id: request_id,
                                template_name: "email_edit_response.html",
                                type: "edit",
                                response_id: response_id,
                                content: first.find('.note-content').val(),
                                privacy: first.find("input[name=privacy]:checked").val(),
                                confirmation: false
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
                            type: "edit",
                            response_id: response_id,
                            content: first.find(".note-content").val(),
                            privacy: first.find("input[name=privacy]:checked").val(),
                            confirmation: true,
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
                    $.ajax({
                        url: "/response/" + response_id,
                        type: "PATCH",
                        data: form.serializeArray(),
                        success: function (response) {
                            location.reload();
                        }
                    });
                });

                // Apply parsley data required validation to note title and url
                first.find('.note-content').attr("data-parsley-required", "");

                // Apply parsley max length validation to note title and url
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

        var deleteConfirmString = sprintf("%s:%s", request_id, response_id);
        deleteConfirmCheck.on("input", function() {
            if ($(this).val() === deleteConfirmString) {
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
