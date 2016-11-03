$(function () {

    var responses = null;
    var index = 0;
    var index_increment = 10;

    var request_id = $('#request-id').text(); // TODO: (maybe) do this for js.html files.

    // get first set of responses on page load
    $.ajax({
        url: '/request/api/v1.0/responses',
        data: {
            start: 0,
            request_id: request_id,
            with_template: true,
        },
        success: function (data) {
            responses = data.responses;
            showResponses();
        },
        error: function (error) {
            console.log(error);
        }
    });

    function showResponses() {
        var response_list = $('#request-responses');
        response_list.empty();

        var file_response_added = false;
        var index_incremented = index + index_increment;
        var end = responses.length < index_incremented ? responses.length : index_incremented;
        for (var i = index; i < end; i++) {
            response_list.append(responses[i].template);
            setEditResponseWorkflow(responses[i].id, responses[i].type);
            if (!file_response_added && responses[i].type === "file") {
                file_response_added = true;
            }
        }
        if (file_response_added) {
            bindFileUpload(
                ".fileupload-update",
                request_id,
                true,
                "template-upload-update",
                "template-download-update"
            );
        }
    }

    function loadMoreResponses() {
        $.ajax({
            url: '/request/api/v1.0/responses',
            data: {
                start: responses.length,
                request_id: request_id,
                with_template: true,
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
        showResponses();
    });

    // TODO: remove (make tooltip for QA)
    $('#request-responses').on('click', '.tmp-save-changes', function () {
        var form = $(this).parents('.modal-body').children('form');
        var response_id = $(this).parents('.modal-content').children('.response-id').text();
        $.ajax({
            url: "/response/" + response_id,
            type: "PUT",
            data: form.serialize(),
            success: function (response) {
                console.log(response);
            }
        });
    });

    // TODO: DELETE updated on modal close and reset

    function setEditResponseWorkflow(response_id, response_type) {

        switch (response_type) { // TODO: other response types
            case "file":
                var response_modal = $("#response-modal-" + response_id);

                var first = response_modal.find('.first');
                var second = response_modal.find('.second');
                var third = response_modal.find('.third');

                var next1 = first.find('.response-modal-next');
                var next2 = second.find('.response-modal-next');
                var prev2 = second.find('.response-modal-prev');
                var prev3 = third.find('.response-modal-prev');

                next1.click(function () {
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
                            tinyMCE.get("email-file-content-" + response_id).setContent(data);
                        }
                    });
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
                            email_content: $("#email-file-content-" + response_id).val()
                        },
                        success: function (data) {
                            // Data should be html template page.
                            third.find(".email-file-summary").html(data);
                        },
                        error: function (error) {
                            console.log(error);
                        }
                    });
                });

                prev2.click(function () {
                    // TODO: error message reset
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
                        value: third.find(".email-file-summary").html()
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

                // Initialize tinymce HTML editor
                tinymce.init({
                    // sets tinymce to enable only on specific textareas classes
                    mode: "specific_textareas",
                    // selector for tinymce textarea classes is set to 'tinymce-area'
                    editor_selector: "tinymce-area",
                    elementpath: false,
                    height: 180
                });

                break;
            default:
                break;
        }
    }

});
