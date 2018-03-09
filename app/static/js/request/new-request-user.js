/**
 * Created by atan on 9/14/16.
 */

"use strict";

$(document).ready(function () {

    $("input[name='tz-name']").val(jstz.determine().name());

    // ajax call to get and populate list of agencies choices based on selected category
    $("#request-category").change(function () {
        $.ajax({
            url: "/request/agencies",
            type: "GET",
            data: {
                category: $("#request-category").val()
            },
            success: function (data) {
                var sel = $("#request-agency");
                sel.empty();
                for (var i = 0; i < data.length; i++) {
                    var opt = document.createElement("option");
                    opt.innerHTML = data[i][1];
                    opt.value = data[i][0];
                    sel.append(opt);
                }
            }
        });
    });

    // ajax call to get additional information for the specified agency
    $("#request-agency").change(function () {
        var selectedAgency = $("#request-agency").val();
        var requestInstructionsDiv = $("#request-agency-instructions");
        var requestInstructionsContentDiv = $("#request-agency-instructions-content");
        $.ajax({
            url: "/agency/feature/" + selectedAgency + "/" + "specific_request_instructions",
            type: "GET",
            success: function (data) {
                requestInstructionsContentDiv.html("<p>" + data["specific_request_instructions"]["text"] + "</p>");
                if (data["specific_request_instructions"]["url"]) {
                    requestInstructionsContentDiv.append("<br /><a rel=\"noopener noreferrer\" target=\"_blank\" href=\"" + data["specific_request_instructions"]["url"]["location"] + "\">" + data["specific_request_instructions"]["url"]["title"] + "</a>")
                }
                requestInstructionsDiv.show();
            },
            error: function () {
                requestInstructionsDiv.hide();
            }

        });
    });

    $("#request-agency-instructions-toggle").click(function () {
        var el = $("#request-agency-instructions-toggle");
        var requestInstructionsContentDiv = $("#request-agency-instructions-content");
        var hideHtml = "<button type=\"button\" id=\"request-agency-instructions-btn\" class=\"btn btn-block btn-info\"><span class=\"glyphicon glyphicon-chevron-up\"></span>&nbsp;&nbsp;Hide Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-up\"></span></button>";
        var showHtml = "<button type=\"button\" id=\"request-agency-instructions-btn\" class=\"btn btn-block btn-info\"><span class=\"glyphicon glyphicon-chevron-down\"></span>&nbsp;&nbsp;Show Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-down\"></span></button>";
        if (el.html() === showHtml) {
            el.html(hideHtml);
            requestInstructionsContentDiv.show();
        } else {
            el.html(showHtml);
            requestInstructionsContentDiv.hide();
        }
    });
    // javascript to add tooltip popovers when selecting the title and description
    $('#request-title').attr({
        'data-placement': "top",
        'data-trigger': "hover focus",
        'data-toggle': "popover",
        'data-content': "Public Advocate Emails from 2015",
        title: "Example Title"
    });
    $('#request-title').popover();
    // $('#request-title').click(function(){
    //     $('#request-title').popover('show');
    // });

    $('#request-description').attr({
        'data-placement': "top",
        'data-trigger': "hover focus",
        'data-toggle': "popover",
        'data-content': "Topic: Public Advocate Emails from 2015. Emails that mention bike lanes or bicycle lanes from the Public Advocate's Office between July 27, 2015 and September 10, 2015.",
        title: "Example Request"
    });
    $('#request-description').click(function () {
        $('#request-description').popover('show');
    });
    $('#request-description').popover();
    // $('#request-description').click(function(){
    //     $('#request-description').popover('show');
    // });

    // Apply parsley validation styles to the input forms for a new request.
    $('#request-title').attr('data-parsley-required', '');
    $('#request-title').attr('data-parsley-maxlength', 90);
    $('#request-agency').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-maxlength', 5000);

    // Limit the size of the file upload to 20 Mb. Second parameter is number of Mb's.
    $('#request-file').attr('data-parsley-max-file-size', "20");

    // Specify container for file input parsley error message
    $('#request-file').attr("data-parsley-errors-container", ".file-error");

    // Set name of the file to the text of filename div if file exists
    $("#request-file").change(function () {
        var file = this.files[0];
        var isChrome = window.chrome;

        if (file) {
            $("#filename").text((this.files[0].name));
        }
        // Cancel is clicked on upload window
        else {
            // If browser is chrome, reset filename text
            if (isChrome) {
                $("#filename").text("");
            }
        }
    });

    // Clear the file from input and the name from filename div
    $("#clear-file").click(function () {
        if ($(".file-error").is(":visible")) {
            $(".file-error").hide();
        }
        $("#request-file").val("");
        $("#filename").text("");
    });

    $('#request-form').parsley().on('form:validate', function () {
        // Do stuff when parsley validates
        // TODO: this or combine (see the other new-request-* js files)
        if ($("#request-file").parsley().isValid() === false) {
            $(".file-error").show();
        }
        else {
            $(".file-error").hide();
        }
    });

    // Clear error messages for form.request_file on submit ...
    $('#submit').click(function () {
        $('.upload-error').remove();
    });
    // ... or on input change for request_file
    $('#request-file').change(function () {
        $('.upload-error').remove();
    });

    // Disable submit button on form submission
    $('#request-form').submit(function () {
        $('#submit').hide();
        $('#processing-submission').show()
    });

    // Character count for creating a new request
    $('#request-title').keyup(function () {
        characterCounter("#title-character-count", 90, $(this).val().length)
    });

    $('#request-description').keyup(function () {
        characterCounter("#description-character-count", 5000, $(this).val().length)
    });

});
