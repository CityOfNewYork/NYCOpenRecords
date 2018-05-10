"use strict";

// Don't cache ajax requests
$.ajaxSetup({cache: false});

$(function () {
    $("[data-toggle='popover']").popover();
});

$(function () {
    $(".disable-enter-submit").keypress(function (e) {
        if (e.keyCode == '13') {
            e.preventDefault();
        }
    });
});

function characterCounter(target, limit, currentLength, minLength) {
    /* Global character counter
     *
     * Parameters:
     * - target: string of target selector
     * - limit: integer of maximum character length
     * - currentLength: integer value of keyed in content
     * - minLength: integer of minimum character length (default = 0)
     *
     * Ex:
     * {
     *     target: "#note-content",
     *     charLength: 500,
     *     contentLength: $(this).val().length,
     *     minLength: 0
     * }
     *
     * */
    var length = limit - currentLength;
    minLength = (typeof minLength !== 'undefined') ? minLength : 0;
    var s = length === 1 ? "" : "s";
    $(target).text(length + " character" + s + " remaining");
    if (length == 0) {
        $(target).css("color", "red");
    } else if (currentLength < minLength) {
        $(target).css("color", "red");
    }
    else {
        $(target).css("color", "black");
    }
}

function regexUrlChecker(value) {
    /* Global regexUrlChecker
     *
     * Checks the value of a url link using regex with one of the following allowed protocols: http, https, ftp, git
     *
     * Parameters:
     * value: string of link url
     *
     * Returns: does value match regex object?
     * */
    var regex = /^(https?|s?ftp|git):\/\/(((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:)*@)?(((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))|((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?)(:\d*)?)(\/((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)+(\/(([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)*)*)?)?(\?((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|[\uE000-\uF8FF]|\/|\?)*)?(#((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|\/|\?)*)?$/i;
    return regex.test(value);
}

/* jquery datepicker */

// An array of holiday dates to be disabled
var holiday_dates = null;

function notHolidayOrWeekend(date, forPicker) {
    /* Global notHolidayOrWeekend
     *
     * http://api.jqueryui.com/datepicker/#option-beforeShowDay
     *
     * WARNING:
     * --------
     * 'holiday_dates' must be set globally before calling this function.
     */
    if (typeof(forPicker) === "undefined") {
        forPicker = true;
    }
    var formattedDate = $.datepicker.formatDate('yy-mm-dd', date);
    var holiday_or_weekend = $.inArray(formattedDate, holiday_dates) !== -1 ||
        date.getDay() === 0 || date.getDay() === 6;
    // TODO: would be nice to display the name of the holiday (tooltip)
    return forPicker ? [!holiday_or_weekend] : !holiday_or_weekend;
}

function getRequestAgencyInstructions() {
    /* Global getAgencyInstructions
     *
     * ajax call to get additional information for the specified agency
     */

    var agencyEin = $("#request-agency").val();
    var requestInstructionsDiv = $("#request-agency-instructions");
    var requestInstructionsContentDiv = $("#request-agency-instructions-content");

    if (agencyEin !== "") {
        $.ajax({
            url: "/agency/feature/" + agencyEin + "/" + "specific_request_instructions",
            type: "GET",
            success: function (data) {
                if (data["specific_request_instructions"]["text"] !== "") {
                    requestInstructionsContentDiv.html("<p>" + data["specific_request_instructions"]["text"] + "</p>");
                    requestInstructionsDiv.show();
                }
                else {
                    requestInstructionsDiv.hide();
                }
            },
            error: function () {
                requestInstructionsDiv.hide();
            }
        });
    }
}

function toggleRequestAgencyInstructions(action) {
    /* Global toggleRequestAgencyInstructions
     *
     * determine whether or not to show agency instruction content
     */
    var el = $("#request-agency-instructions-toggle");
    var requestInstructionsContentDiv = $("#request-agency-instructions-content");
    var hideHtml = "<button type=\"button\" id=\"request-agency-instructions-btn\" class=\"btn btn-block btn-info\"><span class=\"glyphicon glyphicon-chevron-up\"></span>&nbsp;&nbsp;Hide Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-up\"></span></button>";
    var showHtml = "<button type=\"button\" id=\"request-agency-instructions-btn\" class=\"btn btn-block btn-info\"><span class=\"glyphicon glyphicon-chevron-down\"></span>&nbsp;&nbsp;Show Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-down\"></span></button>";

    if (action === "show") {
        el.html(hideHtml);
        requestInstructionsContentDiv.show();
    }
    else if (action === "hide") {
        el.html(showHtml);
        requestInstructionsContentDiv.hide();
    }
    else if (action === "default") {
        if (el.html() === showHtml) {
            el.html(hideHtml);
            requestInstructionsContentDiv.show();
        } else {
            el.html(showHtml);
            requestInstructionsContentDiv.hide();
        }
    }
}

function getCustomRequestForms(agencyEin) {
    /* exported getCustomRequestForms
     *
     * function to determine if custom request forms need to be shown on category or agency change
     */
    var selectedAgency = agencyEin;
    var customRequestFormsDiv = $("#custom-request-forms");
    var requestType = $("#request-type");

    // ajax call to show request type drop down
    requestType.empty();
    $.ajax({
        url: "/agency/feature/" + selectedAgency + "/" + "custom_request_forms",
        type: "GET",
        success: function (data) {
            if (data["custom_request_forms"] === true) {
                customRequestFormsDiv.show();
                // ajax call to populate request type drop down with custom request form options
                $.ajax({
                    url: "/agency/api/v1.0/custom_request_forms/" + selectedAgency,
                    type: "GET",
                    success: function (data) {
                        requestType.append(new Option("", ""));
                        for (var i = 0; i < data.length; i++) {
                            requestType.append(new Option(data[i][1], data[i][0]));
                        }
                    }
                });
            }
            else {
                customRequestFormsDiv.hide();
            }
        },
        error: function () {
            customRequestFormsDiv.hide();
        }
    });
}

function renderCustomRequestForm() {
    /*
     * function to render custom form fields based on their field definitions
     */
    var formId = $("#request-type").val();
    var agencyEin = $("#request-agency").val();

    if (formId !== "") {
        $.ajax({
            url: "/agency/api/v1.0/custom_request_form_fields",
            type: "GET",
            data: {
                form_id: formId,
                agency_ein: agencyEin
            },
            success: function (data) {
                // TODO (johnyu95): Print actual form out.
                console.log(data);
            }
        });
    }
}
