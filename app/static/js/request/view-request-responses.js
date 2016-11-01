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
            bindFileUpload()
        }
    }

    function createResponseRow(num, response) {
        // Now this right here is a good case for a js framework
        // If this is too nasty, we can try fetching and converting html files...
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
                    </div>
                    <div class="modal-body">`,
            response.id,
            response.id,
            response.type.toUpperCase());

        switch(response.type) {
            case "file":
                modal += sprintf(`
                    <form class="fileupload-update fileupload-form" action="/response/%s" method="POST">
                        <div>
                            <a href="" id="uploaded-filename-%s">%s</a>
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
                                <input type="text" name="title" value="%s">
                            </div>
                        </label>
                        <div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="release_public" %s>
                                    Release and Public
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="release_private" %s>
                                    Release and Private
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="privacy" value="private" %s>
                                    Private
                                </label>
                            </div>
                        </div>
                    </form>`,
                    response.id,
                    response.id,
                    response.metadata.name,
                    response.metadata.title,
                    response.privacy == "release_public" ? "checked" : "",
                    response.privacy == "release_private" ? "checked" : "",
                    response.privacy == "private" ? "checked" : ""
                );
                break;
            default:
                modal += "<p>Nothing to see here folks.</p>";
                break;
        }

        modal += `
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-danger pull-left">Delete</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary">Save Changes</button>
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

    $('#request-responses').on('click', '.response-row', function() {

    });

    function bindFileUpload() {
        $('.fileupload-update').fileupload({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            uploadTemplateId: 'template-upload-update',
            downloadTemplateId: 'template-download-update',
            url: '/upload/' + '{{ request.id }}',
            formData: {
                update: true
            },
            maxChunkSize: 512000,  // 512 kb
            maxFileSize: 500000000,  // 500 mb
            // autoUpload: true,
            chunksend: function (e, data) {
                if (data.context[0].abortChunkSend) {
                    return false;
                }
            },
            chunkdone: function (e, data) {
                // stop sending chunks on error
                if (data.result) {
                    if (data.result.files[0].error) {
                        data.context[0].abortChunkSend = true;
                        data.files[0].error = data.result.files[0].error
                    }
                }
            },
            chunkfail: function (e, data) {
                // remove existing partial upload
                $.ajax({
                    type: "DELETE",
                    url: '/upload/request/' +
                    '{{ request.id }}/' +
                    encodeName(data.files[0].name),
                    data: {
                        quarantined_only: true
                    }
                });
            }
        }).bind('fileuploaddone', function (e, data) {
            var filename = data.result.files[0].name;
            var htmlId = encodeName(filename);
            data.result.files[0].identifier = htmlId;
            setTimeout(
                    pollUploadStatus.bind(null, filename, htmlId),
                    4000); // McAfee Scanner min 3+ sec startup
        }).bind('fileuploadadd', function (e, data) {
            // Delete already added file
            var elem_files = $('.fileupload-update').find('.files');
            var templates_upload = elem_files.children('.template-upload');
            var templates_download = elem_files.children('.template-download');
            if (templates_upload.length > 0) {
                templates_upload.remove();
            }
            if (templates_download.length > 0) {
                for (var i = 0; i < templates_download.length; i++) {
                    var file_identifier = $(templates_download[i]).attr('id');
                    // if this template is for a successful upload
                    if (typeof file_identifier != 'undefined') {
                        deleteUpdated($(templates_download[i]));
                    }
                    $(templates_download[i]).remove();
                }
            }
            $('.fileupload-loading').hide();
            $('.fileupload-process').hide();
        });
    }

});
