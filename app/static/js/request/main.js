"use strict";

// Don't cache ajax requests
$.ajaxSetup({cache: false});

$(function () {
    $("[data-toggle='popover']").popover();
});

$(function () {
    $(".disable-enter-submit").keypress(function (e) {
        if (e.keyCode === "13") {
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
    minLength = (typeof minLength !== "undefined") ? minLength : 0;
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
    var formattedDate = $.datepicker.formatDate("yy-mm-dd", date);
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

// variables used to handle custom forms
var showMultipleRequestTypes = false; // determines if that agency's custom forms can be repeated
var repeatableCounter = {}; // tracks how many more repeatable options can be rendered
var previousValues = []; // tracks the previous values of each request type dropdown
var currentValues = []; // tracks the current values of each request type dropdown
var customRequestFormCounter = 1; // tracks how many request type dropdowns have been rendered
var dismissTarget = ""; // tracks which dismiss button is being clicked
var customRequestFormData = {}; // tracks the data of custom forms that will be sent on submit

function getCustomRequestForms(agencyEin) {
    /* exported getCustomRequestForms
     *
     * function to determine if custom request forms need to be shown on category or agency change
     */
    repeatableCounter = {};
    customRequestFormCounter = 1;

    var selectedAgency = agencyEin;
    var customRequestPanelDiv = $("#custom-request-panel-" + customRequestFormCounter.toString());
    var customRequestFormsDivId = "#custom-request-forms-" + customRequestFormCounter.toString();
    var requestTypeId = "#request-type-" + customRequestFormCounter.toString();
    var customRequestFormId = "#custom-request-form-content-" + customRequestFormCounter.toString();
    var customRequestFormsDiv = $(customRequestFormsDivId);
    var requestType = $(requestTypeId);
    var customRequestFormContent = $(customRequestFormId);
    var customRequestFormAdditionalContent = $("#custom-request-form-additional-content");

    requestType.empty();
    customRequestFormContent.html("");
    customRequestFormContent.hide();
    customRequestFormAdditionalContent.hide();
    // ajax call to show request type drop down
    $.ajax({
        url: "/agency/feature/" + selectedAgency + "/" + "custom_request_forms",
        type: "GET",
        success: function (data) {
            if (data["custom_request_forms"]["enabled"] === true) {
                // ajax call to populate request type drop down with custom request form options
                $.ajax({
                    url: "/agency/api/v1.0/custom_request_forms/" + selectedAgency,
                    type: "GET",
                    success: function (data) {
                        if (data.length === 1) {
                            // if only one option, render that form by default
                            repeatableCounter[[data[0][0]]] = data[0][2];
                            requestType.append(new Option(data[0][1], data[0][0]));
                            previousValues[0] = "";
                            currentValues[0] = "";
                            customRequestPanelDiv.show();
                            customRequestFormsDiv.show();
                            renderCustomRequestForm("1"); // render the form to the first custom request form content div
                            if (moreOptions()) {
                                customRequestFormAdditionalContent.show();
                            }
                        }
                        else {
                            requestType.append(new Option("", ""));
                            for (var i = 0; i < data.length; i++) {
                                repeatableCounter[data[i][0]] = data[i][2]; // set the keys to be the form id
                                var option = new Option(data[i][1], data[i][0]);
                                requestType.append(option);
                            }
                            previousValues[0] = "";
                            currentValues[0] = "";

                            customRequestPanelDiv.show();
                            customRequestFormsDiv.show();
                        }
                    }
                });
                // check if custom forms are repeatable
                if (data["custom_request_forms"]["multiple_request_types"] === true) {
                    showMultipleRequestTypes = true;
                }
                else {
                    showMultipleRequestTypes = false;
                }
            }
            else {
                customRequestPanelDiv.hide();
                customRequestFormsDiv.hide();
            }
        },
        error: function () {
            customRequestPanelDiv.hide();
            customRequestFormsDiv.hide();
        }
    });
}

function populateDropdown(agencyEin) {
    /*
     * function to populate any empty request type dropdowns
     */
    var selectedAgency = agencyEin;
    var customRequestFormsDivId = "#custom-request-forms-" + customRequestFormCounter.toString();
    var customRequestFormsDiv = $(customRequestFormsDivId);
    var customRequestFormAdditionalContent = $("#custom-request-form-additional-content");;

    $(".request-type").each(function(){
        if (this.length === 0) { // if this is an unpopulated dropdown
            var requestType = this;
            $.ajax({
                url: "/agency/api/v1.0/custom_request_forms/" + selectedAgency,
                type: "GET",
                success: function (data) {
                    if (data.length === 1) {
                        requestType.append(new Option(data[0][1], data[0][0]));
                        customRequestFormsDiv.show();
                        renderCustomRequestForm(customRequestFormCounter);
                        if (moreOptions()) {
                            customRequestFormAdditionalContent.show();
                        }
                    }
                    else {
                        requestType.append(new Option("", ""));
                        for (var i = 0; i < data.length; i++) {
                            var option = new Option(data[i][1], data[i][0]);
                            if (repeatableCounter[data[i][0]] === 0) {
                                // if all possible instances of the form have been rendered then disable the option
                                option.disabled = true;
                            }
                            requestType.append(option);
                        }
                    }
                }
            });
        }
    });
}

function updateCustomRequestFormDropdowns() {
    /*
     * Update the dropdowns to disable options where they are no longer repeatable.
     */
    $(".request-type").each(function(){
        var requestTypeOptions = "#" + this.id + " > option";
        $(requestTypeOptions).each(function () {
            if (repeatableCounter[this.value] === 0) {
                $(this).attr("disabled", "disabled");
            }
            else {
                $(this).removeAttr("disabled");
            }
        });
    });
}

function renderCustomRequestForm(target) {
    /*
     * function to render custom form fields based on their field definitions.
     * target is the instance number of divs that the form will be rendered to
     */
    var requestTypeId = "#request-type-" + target;
    var requestType = $(requestTypeId);
    var formId = $(requestType).val();
    var agencyEin = $("#request-agency").val();
    var customRequestFormId = "#custom-request-form-content-" + target;
    var customRequestFormContent = $(customRequestFormId);
    var customRequestFormAdditionalContent = $("#custom-request-form-additional-content");

    if (formId !== "") {
        $.ajax({
            url: "/agency/api/v1.0/custom_request_form_fields",
            type: "GET",
            data: {
                form_id: formId,
                agency_ein: agencyEin,
                repeatable_counter: JSON.stringify(repeatableCounter)
            },
            success: function (data) {
                // update the values in the tracking variables
                currentValues[target-1] = formId;

                detectChange(); // determine which request type dropdown was changed

                customRequestFormContent.html(data);
                previousValues[target-1] = formId;
                updateCustomRequestFormDropdowns();

                try {
                    // render datepicker plugins
                    $(".custom-request-form-datepicker").datepicker({
                        dateFormat: "mm/dd/yy",
                        maxDate: 0
                    }).keydown(function (e) {
                        // prevent keyboard input except for tab
                        if (e.keyCode !== 8 &&
                            e.keyCode !== 9 &&
                            e.keyCode !== 37 &&
                            e.keyCode !== 39 &&
                            e.keyCode !== 48 &&
                            e.keyCode !== 49 &&
                            e.keyCode !== 50 &&
                            e.keyCode !== 51 &&
                            e.keyCode !== 52 &&
                            e.keyCode !== 53 &&
                            e.keyCode !== 54 &&
                            e.keyCode !== 55 &&
                            e.keyCode !== 56 &&
                            e.keyCode !== 57 &&
                            e.keyCode !== 191)
                            e.preventDefault();
                    });
                }
                catch (err) {
                    // if one of the forms doesn't have a date field it will throw an error when you try to render it
                    // TODO: find a better way to handle this error
                }

                try {
                    // render timepicker plugins
                    $(".timepicker").timepicker({
                        timeFormat: "h:mm p",
                        interval: 1,
                        minTime: "12:00am",
                        maxTime: "11:59pm",
                        startTime: "12:00am",
                        dynamic: false,
                        dropdown: true,
                        scrollbar: true
                    }).keydown(function (e) {
                        // prevent keyboard input except for allowed keys
                        if (e.keyCode !== 8 &&
                            e.keyCode !== 9 &&
                            e.keyCode !== 37 &&
                            e.keyCode !== 39 &&
                            e.keyCode !== 48 &&
                            e.keyCode !== 49 &&
                            e.keyCode !== 50 &&
                            e.keyCode !== 51 &&
                            e.keyCode !== 52 &&
                            e.keyCode !== 53 &&
                            e.keyCode !== 54 &&
                            e.keyCode !== 55 &&
                            e.keyCode !== 56 &&
                            e.keyCode !== 57 &&
                            e.keyCode !== 16 &&
                            e.keyCode !== 65 &&
                            e.keyCode !== 77 &&
                            e.keyCode !== 80 &&
                            e.keyCode !== 186)
                            e.preventDefault();
                    });

                }
                catch (err) {
                    // if one of the forms doesn't have a time field it will throw an error when you try to render it
                    // TODO: find a better way to handle this error
                }

                // Do not reset on click
                $(".select-multiple").find("option").mousedown(function (e) {
                    e.preventDefault();
                    $(".select-multiple").focus();
                    $(this).prop("selected", !$(this).prop("selected"));
                    return false;
                });

                customRequestFormContent.show();
                // check to show add new request information button
                if (showMultipleRequestTypes === true) {
                    // check if repeatable counter still has options
                    if (moreOptions()) {
                        customRequestFormAdditionalContent.show();
                    }
                    else {
                        customRequestFormAdditionalContent.hide();
                    }
                }
                else {
                    customRequestFormAdditionalContent.hide();
                }
            }
        });
    }
    else {
        customRequestFormContent.html("");
        customRequestFormContent.hide();
        customRequestFormAdditionalContent.hide();

        // update the values in the tracking variables
        currentValues[target-1] = "";

        detectChange();

        previousValues[target-1] = "";
        updateCustomRequestFormDropdowns();
    }
}

function moreOptions() {
    /*
     * Determine if there are still forms that can be repeated in the request.
     * Return true if there is at least one form that can be rendered.
     * Return false if all options have been rendered already.
     */
    for (var key in repeatableCounter) {
        if (repeatableCounter[key] !== 0) return true;
    }
    return false;
}

function detectChange() {
    /*
     * Detects which request type dropdown was changed and updates the repeatable counter accordingly
     */
    for (var i = 0; i < currentValues.length; i++) {
        if (currentValues[i] !== previousValues[i]) {
            if (previousValues[i] !== "") {
                repeatableCounter[previousValues[i]] = repeatableCounter[previousValues[i]] + 1;
            }

            if (currentValues[i] !== "") {
                repeatableCounter[currentValues[i]] = repeatableCounter[currentValues[i]] - 1;
            }
        }
    }
}

function handlePanelDismiss() {
    /*
     * handle the dismissal of a custom request panel. Target is the data target of the dismiss button
     */
    // +1 to repeatable counter and reset previousValues/currentValues array
    var targetId = dismissTarget.replace("#panel-dismiss-button-", "");
    var panelId = dismissTarget.replace("#panel-dismiss-button-", "#custom-request-panel-");
    if (currentValues[targetId-1] !== "") {
                repeatableCounter[currentValues[targetId-1]] = repeatableCounter[currentValues[targetId-1]] + 1;
                previousValues[targetId-1] = "";
                currentValues[targetId-1] = "";
    }
    updateCustomRequestFormDropdowns();

    // show additional content button if repeatable counter has more options and it is the last one
    if (targetId === customRequestFormCounter.toString()) {
        if (moreOptions()) {
            $("#custom-request-form-additional-content").show();
        }
    }

    // remove custom request panel div
    $(panelId).remove();
}

function processCustomRequestFormData() {
    /*
     * Process the custom request form data into a JSON to be passed back on submit
     */
    var formNumber = 1;
    var fieldNumber = 1;
    for (var i = 0; i < currentValues.length; i++) {
        if (currentValues[i] !== "") {
            var target = (i + 1).toString();
            var formKey = "form_";
            var fieldKey = "field_";
            var formName = $("#request-type-" + target + " option:selected").text();
            var previousRadioId = "";

            // add leading zero to forms less than 10 so they can be properly sorted
            if (formNumber < 10) {
                formKey = formKey + "0" + formNumber;
            }
            else {
                formKey = formKey + formNumber;
            }

            customRequestFormData[formKey] = {};
            customRequestFormData[formKey]["form_name"] = formName;
            customRequestFormData[formKey]["form_fields"] = {};

            // loop through each form field to get the value
            $("#custom-request-form-content-" + target + " > .custom-request-form-field > .custom-request-form-data").each(function () {
                var fieldName = $("label[for='" + this.id + "']").html();
                // add leading zero to fields less than 10 so they can be properly sorted
                if (fieldNumber < 10) {
                    fieldKey = fieldKey + "0" + fieldNumber;
                }
                else {
                    fieldKey = fieldKey + fieldNumber;
                }
                customRequestFormData[formKey]["form_fields"][fieldKey] = {};
                customRequestFormData[formKey]["form_fields"][fieldKey]["field_name"] = fieldName;

                if ($("#" + this.id).prop("multiple") === true) {
                    var selectMultipleId = "#" + this.id;
                    customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = $(selectMultipleId).val();
                }
                else if ($("#" + this.id).is(":radio") === true) {
                    // since all radio inputs have the same id only take the value of the first one to avoid duplicates
                    var radioValue = $("input[name='" + this.id + "']:checked").val();
                    if (this.id !== previousRadioId) {
                        customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = radioValue;
                    }
                    else {
                        fieldNumber--;
                    }
                    previousRadioId = this.id;
                }
                else {
                    customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = this.value;
                }
                fieldNumber++;
                fieldKey = "field_";
            });
            formNumber++;
            fieldNumber = 1;
        }
    }
    $("#custom-request-forms-data").val(JSON.stringify(customRequestFormData));
}