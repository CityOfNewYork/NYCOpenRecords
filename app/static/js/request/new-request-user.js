/**
 * Created by atan on 9/14/16.
 */

/* globals characterCounter: true */
/* globals getRequestAgencyInstructions: true */
/* globals getCustomRequestForms: true */
/* globals toggleRequestAgencyInstructions: true */
/* globals renderCustomRequestForm: true */

"use strict";

var requiredFields = ["request-agency", "request-title", "request-description", "first-name", "last-name", "email",
    "phone", "fax", "address-line-1", "method-received", "request-date", "city", "zipcode"];

$(document).ready(function () {
    $(window).load(function () {
        // Determine if the agencyRequestInstructions need to be shown on page load.
        getRequestAgencyInstructions();
    });

    $("input[name='tz-name']").val(jstz.determine().name());
    
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
                // Determine if the agencyRequestInstructions need to be shown on page load.
                getRequestAgencyInstructions();
                toggleRequestAgencyInstructions("show");
                $(".appended-div").remove(); // remove the appended divs from previous agency
                previousValues = [];
                currentValues = [];
                getCustomRequestForms(sel.find("option:first-child").val());
            }
        });
    });

    $("#request-agency").change(function () {
        getRequestAgencyInstructions();
        toggleRequestAgencyInstructions("show");
        $(".appended-div").remove(); // remove the appended divs from previous agency
        previousValues = [];
        currentValues = [];
        getCustomRequestForms($("#request-agency").val());
    });

    $("#request-agency-instructions-toggle").click(function () {
        toggleRequestAgencyInstructions("default");
    });

    $(document).on("focus", ".request-type", function () {
        var target = document.activeElement.id;
        target = target.replace("request-type-", "");
        var targetId = "#" + document.activeElement.id;
        $(targetId).off().change(function () {
            renderCustomRequestForm(target);
        });
    });

    // determine which dismiss button is being clicked
    $(document).on("click", ".panel-dismiss", function () {
        dismissTarget = "#" + document.activeElement.id;
    });

    // append a new dropdown and content div every time the additional content button is clicked
    $("#custom-request-form-additional-content").click(function () {
        customRequestFormCounter = customRequestFormCounter + 1;
        var dropdownTemplate = "<div class='panel panel-default appended-div' id='custom-request-panel-" + customRequestFormCounter + "'><div class='panel-heading' id='custom-request-forms-" + customRequestFormCounter + "' style='display: block;'><label class='request-heading request-type-label' for='request_type'>Request Type (optional)</label><button type='button' class='close panel-dismiss' id='panel-dismiss-button-" + customRequestFormCounter + "' data-target='#panel-dismiss-modal' data-toggle='modal'><span aria-hidden='true'>&times;</span><span class='sr-only'>Close</span></button><select class='input-block-level request-type' id='request-type-" + customRequestFormCounter + "' name='request_type'></select><br></div>";
        var contentTemplate = "<div class='panel-body' id='custom-request-form-content-" + customRequestFormCounter + "' hidden></div></div>";
        $(dropdownTemplate + contentTemplate).insertBefore("#custom-request-form-additional-content");
        $("#custom-request-form-additional-content").hide();

        // populate any empty dropdowns with that agency's form options
        populateDropdown($("#request-agency").val());

        previousValues[customRequestFormCounter-1] = "";
        currentValues[customRequestFormCounter-1] = "";
    });

     // Loop through required fields and apply a data-parsley-required attribute to them
    for (var i = 0; i < requiredFields.length; i++) {
        $("#" + requiredFields[i]).attr("data-parsley-required", "");
    }

    // javascript to add tooltip popovers when selecting the title and description
    $("#request-title").attr({
        "data-placement": "top",
        "data-trigger": "hover focus",
        "data-toggle": "popover",
        "data-content": "Public Advocate Emails from 2015",
        title: "Example Title"
    });
    $("#request-title").popover();
    // $("#request-title").click(function(){
    //     $("#request-title").popover("show");
    // });

    $("#request-description").attr({
        "data-placement": "top",
        "data-trigger": "hover focus",
        "data-toggle": "popover",
        "data-content": "Topic: Public Advocate Emails from 2015. Emails that mention bike lanes or bicycle lanes from the Public Advocate's Office between July 27, 2015 and September 10, 2015.",
        title: "Example Request"
    });
    $("#request-description").click(function () {
        $("#request-description").popover("show");
    });
    $("#request-description").popover();
    // $("#request-description").click(function(){
    //     $("#request-description").popover("show");
    // });

    // Apply parsley validation styles to the input forms for a new request.
    $("#request-title").attr("data-parsley-maxlength", 90);
    $("#request-description").attr("data-parsley-maxlength", 5000);

    // Limit the size of the file upload to 20 Mb. Second parameter is number of Mb's.
    $("#request-file").attr("data-parsley-max-file-size", "20");

    // Specify container for file input parsley error message
    $("#request-file").attr("data-parsley-errors-container", ".file-error");

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

    $("#request-form").parsley().on("form:validate", function () {
        // Do stuff when parsley validates
        // TODO: this or combine (see the other new-request-* js files)
        if ($("#request-file").parsley().isValid() === false) {
            $(".file-error").show();
        }
        else {
            $(".file-error").hide();
        }
    });

    // Clear error messages for form.request_file on submit .
    $("#submit").click(function () {
        $(".upload-error").remove();
    });
    // . or on input change for request_file
    $("#request-file").change(function () {
        $(".upload-error").remove();
    });

    // Disable submit button on form submission
    $("#request-form").submit(function () {
        processCustomRequestFormData();

        // Prevent multiple submissions
        $(this).submit(function () {
            return false;
        });
        $("#submit").hide();
        $("#processing-submission").show();
    });

    // Character count for creating a new request
    $("#request-title").keyup(function () {
        characterCounter("#title-character-count", 90, $(this).val().length);
    });

    $("#request-description").keyup(function () {
        characterCounter("#description-character-count", 5000, $(this).val().length);
    });

});
