/* global $, window */

$(function () {
    'use strict';

    // Initialize the jQuery File Upload widget:
    $('#fileupload').fileupload({
        // Uncomment the following to send cross-domain cookies:
        //xhrFields: {withCredentials: true},
        url: '/upload/FOIL-XXX',  // dummy request_id
        maxChunkSize: 512000,  // 512 kb
        maxFileSize: 500000000,  // 500 mb
        chunksend: function(e, data) {
            if (data.context[0].abortChunkSend) {
                return false;
            }
        },
        chunkdone: function(e, data) {
            if (data.result) {
                if (data.result.files[0].error) {
                    data.context[0].abortChunkSend = true;
                    data.files[0].error = data.result.files[0].error
                }
            }
        }
    });

    // Enable iframe cross-domain access via redirect option:
    $('#fileupload').fileupload(
        'option',
        'redirect',
        window.location.href.replace(
            /\/[^\/]*$/,
            '/cors/result.html?%s'
        )
    );


    // // Load existing files:
    // $('#fileupload').addClass('fileupload-processing');
    // $.ajax({
    //     // Uncomment the following to send cross-domain cookies:
    //     //xhrFields: {withCredentials: true},
    //     url: $('#fileupload').fileupload('option', 'url'),
    //     dataType: 'json',
    //     context: $('#fileupload')[0]
    // }).always(function () {
    //     $(this).removeClass('fileupload-processing');
    // }).done(function (result) {
    //     $(this).fileupload('option', 'done')
    //         .call(this, $.Event('done'), {result: result});
    // });

});
