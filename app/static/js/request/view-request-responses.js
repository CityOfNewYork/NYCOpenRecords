$(document).ready(function () {

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
            error: function(error) {
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
    nav_buttons.find('.next').click(function() {
        index += index_increment;
        if (index == responses.length - index_increment) {
            loadMoreResponses();
        }
        showResponses();
    });

    // TODO: div blocks instead of this:
    $('#request-responses').on('click', '.tmp-save-changes', function() {
        var form = $(this).parents('.modal-footer').siblings('.modal-body').children('form');
        var response_id = $(this).parents('.modal-footer').siblings('.modal-header').children('.response-id').text();
        $.ajax({
            url: "/response/" + response_id,
            type: "PUT",
            data: form.serialize(),
            success: function(response) {
                console.log(response);
            }
        });
    });

    // TODO: DELETE updated on modal close and reset
});
