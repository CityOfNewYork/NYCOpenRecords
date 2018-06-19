"use strict";

function bindFileUpload(target,
                        request_id,
                        duplicateFileModal,
                        for_update,
                        response_id,
                        uploadTemplateId,
                        downloadTemplateId,
                        nextButton
                        ) {
    /*
    Binds jquery file upload to the element identified by 'target'

    @param {string} target - jquery selector string (ex. "#fileupload")
    @param {string} request_id - FOIL request id
    @param {selector} duplicateFileModal - jQuery selector for duplicate file alert modal
    @param {bool} for_update - editing a file?
    @param {int} response_id - response id of file being replaced
    @param {string} uploadTemplateId - jquery file upload uploadTemplateId
    @param {string} downloadTemplateId - jquery file upload downloadTemplateId
    @param {selector} nextButton - jquery selector for next button of file response workflow
    */

    uploadTemplateId = uploadTemplateId || "template-upload";
    downloadTemplateId = downloadTemplateId || "template-download";

    // var isIE = /*@cc_on!@*/false || !!document.documentMode;
  
    $(target).fileupload({
        //xhrFields: {withCredentials: true},  // send cross-domain cookies
        url: "/upload/" + request_id,
        formData: for_update ? {update: true, response_id: response_id} : {},
        uploadTemplateId: uploadTemplateId,
        downloadTemplateId: downloadTemplateId,
        maxChunkSize: 512000,  // 512 kb
        maxFileSize: 500000000, // 500 mb
        // maxNumberOfFiles: isIE ? 10 : 1000,
        chunksend: function (e, data) {
            // stop sending chunks if abort signaled
            if (data.context[0].abortChunkSend) {
                return false;
            }
        },
        chunkdone: function (e, data) {
            // on error, signal to stop sending chunks
            if (data.result) {
                if (data.result.files[0].error) {
                    data.context[0].abortChunkSend = true;
                    data.files[0].error = data.result.files[0].error
                }
            }
        },
        chunkfail: function (e, data) {
            // remove existing partial upload
            deleteUpload(request_id, encodeName(data.files[0].name), false, true);
            // Re-enable 'next' button
            if (for_update) {
                $(nextButton).attr('disabled', false);
            }
        }
    }).bind("fileuploaddone", function (e, data) {
        // blueimp says that this will only be called on a successful upload
        // so I'm not sure why I have to check for errors here!
        var file = data.result.files[0];
        if (file.errors === undefined) {
            // start polling status endpoint after scanner startup
            var idVal = encodeName(file.name);
            data.result.files[0].identifier = idVal;
            setTimeout(
                pollUploadStatus.bind(null, file.name, idVal, request_id, for_update, nextButton),
                4000);  // McAfee Scanner minimum 3+ second startup
        }
        else {
            // Re-enable 'next' button
            if (for_update) {
                $(nextButton).attr('disabled', false);
            }
        }
    }).bind("fileuploadadd", function (e, data) {
        if (for_update) {
            var elem_files = $(target).find(".files");
            var templates_upload = elem_files.children(".template-upload");
            var templates_download = elem_files.children(".template-download");
            // Remove template for added file (pre-upload)
            if (templates_upload.length > 0) {
                templates_upload.remove();
            }
            // Remove template for uploaded file and delete corresponding file
            if (templates_download.length > 0) {
                for (var i = 0; i < templates_download.length; i++) {
                    var file_identifier = $(templates_download[i]).attr("id");
                    if (typeof file_identifier != "undefined") {
                        // if this template is for a successful upload
                        deleteUpload(request_id, file_identifier, true);
                    }
                    $(templates_download[i]).remove();
                }
            }
        }
        else {
            // Prevent duplicate files from being added
            var currentFiles = [];
            $(this).fileupload("option").filesContainer.children().each(function () {
                currentFiles.push($.trim($(".original-name", this).text()));
            });
            data.files = $.map(data.files, function (file, i) {
                if ($.inArray(file.name, currentFiles) >= 0) {
                    var modalBody = $(duplicateFileModal).find(".modal-body");
                    modalBody.html("<p>The file '" + file.name + "' has already been added.");
                    $(duplicateFileModal).modal('show');
                    return null;
                }
                return file;
            });
        }
        $(".fileupload-loading").hide();
        $(".fileupload-process").hide();
    }).bind("fileuploadstarted", function (e, data) {
        // Disable 'next' button
        if (for_update) {
            $(nextButton).attr('disabled', true);
        }
    });
}

function encodeName(name) {
    /*
    Returns an encoded (base64 without padding) version of 'name' intended
    for use as/in an html id attribute or for use in a url.
    Padding is removed because '=' is an invalid character for an html id
    and it is reserved character for urls.
     */
    return window.btoa(name).replace(/=/g, "");
}

function pollUploadStatus(upload_filename, htmlId, request_id, for_update, nextButton) {
    /*
    Sends a request to the upload status endpoint
    every 2 seconds until it receives a message indicating
    the upload has completed or until it receives an error
    message, then updates the download template.
     */
    $.ajax({
        type: "GET",
        url: "/upload/status",
        data: {
            request_id: request_id,
            filename: upload_filename,
            for_update: for_update
        },
        dataType: "json",
        success: function(response) {
            var tr = $("#".concat(htmlId));
            if (response.error) {
                // Reveal error message
                tr.find(".error-post-fileupload").removeClass("hidden");
                tr.find(".error-post-fileupload-msg").text("Error processing file.");  // scanning, really
                tr.find(".processing-upload").remove();
                setRemoveBtn(request_id, tr.find(".remove-post-fileupload"),
                    false);  // file already deleted
            }
            else if (response.status != "ready") {
                setTimeout(pollUploadStatus.bind(
                    null, upload_filename, htmlId, request_id, for_update, nextButton
                ), 2000);
            }
            else {
                // Reveal full template
                tr.find(".fileupload-input-fields").removeClass("hidden");
                tr.find(".processing-upload").remove();
                setRemoveBtn(request_id, tr.find(".remove-post-fileupload"), true, for_update);
                if (for_update) {
                    // Enable 'next' button
                    $(nextButton).attr('disabled', false)
                }
            }
        }
    });
}

function deleteUpload(request_id,
                      filecode,
                      updated_only,
                      quarantined_only) {
    /*
    Send a DELETE request to the upload endpoint.
     */
    var data = {};
    if (updated_only) {
        data = {updated_only: true}
    }
    else if (quarantined_only) {
        data = {quarantined_only: true}
    }

    $.ajax({
        type: "DELETE",
        url: sprintf("/upload/request/%s/%s",
            request_id, filecode),
        data: data
    });
}

function setRemoveBtn(request_id, button, sendDelete, for_update) {
    /*
    Reveal remove button and set its click event handler.
     */
    sendDelete = sendDelete || true;
    button.removeClass("hidden");
    button.click(function(e) {
        e.preventDefault();
        var template = $(this).closest(".template-download");
        if (sendDelete) {
            deleteUpload(request_id, template.attr("id"), for_update);
        }
        template.remove();
    });
}
