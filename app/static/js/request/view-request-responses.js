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
            request_id: request_id
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
            response_list.append(createResponseRow(i + 1, responses[i]));
            if (responses[i].type === "file") {
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

    function createResponseRow(num, response) {
        // TODO: make a single request instead that concatenates rendered_templates
        var row = sprintf(`
            <div class="row response-row" data-toggle="modal" data-target="#response-modal-%s">
                <div class="col-md-1 response-row-num">%s</div>
                <div class="col-md-2"><strong>%s</strong></div>
                <div class="col-md-5 metadata-preview">%s</div>
                <div class="col-md-4">%s</div>
            </div>`,
            response.id,
            num,
            response.type.toUpperCase(),
            response.preview,
            response.date_modified);

        var modal = sprintf(`
        <div class="modal fade" id="response-modal-%s" tabindex="-1" 
        role="dialog" aria-labelledby="#response-modal-label-%s">
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" 
                        aria-label="Close"><span aria-hidden="true">&times;</span></button>
                        <h4 class="modal-title">%s</h4>
                        <span class="response-id" hidden>%s</span>
                    </div>
                    <div class="modal-body">`,
            response.id,
            response.id,
            response.type.toUpperCase(),
            response.id);

        switch(response.type) {
            case "file":
                var args = {
                    resp_id: response.id,
                    filename: response.metadata.name,
                    title: response.metadata.title,
                    rpub: response.privacy == "release_public" ? "checked" : "",
                    rpriv: response.privacy == "release_private" ? "checked" : "",
                    priv: response.privacy == "private" ? "checked" : ""
                };
                modal += sprintf(`
                    <form class="fileupload-update fileupload-form" action="/response/%(resp_id)s" method="POST">
                        <div>
                            <a href="" id="uploaded-filename-%(resp_id)s">%(filename)s</a>
                        </div>
                        <br>
                        <div class="fileupload-control">
                            <div class="fileupload-error-messages"></div>
                            <div class="fileupload-divs">
                                <div class="row fileupload-buttonbar">
                                    <span class="btn btn-default fileinput-button">
                                        <i class="glyphicon glyphicon-open-file"></i>
                                        <span>Replace File</span>
                                        <input type="file" name="file" id="add-files">
                                    </span>
                                    <span class="fileupload-process"></span>
                                </div>
                                <div role="presentation">
                                    <div class="files"></div>
                                </div>
                            </div>
                        </div>
                        <label for="title">
                            <div class="input-group">
                                <span class="input-group-addon" id="basic-addon1">Title</span>
                                <input type="text" name="title" value="%(title)s">
                            </div>
                        </label>
                        <div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="release_public" %(rpub)s>
                                    Release and Public
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="release_private" %(rpriv)s>
                                    Release and Private
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="private" %(priv)s>
                                    Private
                                </label>
                            </div>
                        </div>
                    </form>`, args);
                break;
            default:
                modal += "<p>Nothing to see here folks.</p>";
                break;
        }

        modal += `
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-danger pull-left disabled">Delete</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary tmp-save-changes">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>`;

        return row + modal;
    }

    function loadMoreResponses() {
        $.ajax({
            url: '/request/api/v1.0/responses',
            data: {
                start: responses.length,
                request_id: request_id
            },
            success: function (data) {
                responses = responses.concat(data.responses);
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
