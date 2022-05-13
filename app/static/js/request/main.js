/* globals requiredFields: true */
"use strict";
var showPIIWarning = true;

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

function characterCounter(target, maxLength, currentLength, minLength) {
    /* Global character counter
     *
     * Parameters:
     * - target: string of target selector
     * - maxLength: integer of maximum character length
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
    var length = maxLength - currentLength;
    minLength = (typeof minLength !== "undefined") ? minLength : 0;
    var s = length === 1 ? "" : "s";
    $(target).text(length + " character" + s + " remaining");
    if (length <= 0) {
        $(target).text(0 + " character" + s + " remaining");
        $(target).css("color", "red");
    } else if (currentLength < minLength) {
        $(target).css("color", "red");
    } else {
        $(target).css("color", "black");
    }
}

function generateCharacterCounterHandler(id, maxLength, minLength) {
    /*
     * This function creates character counter handlers for when you have multiple events inside a loop
     */
    return function () {
        characterCounter("#" + id + "-character-count", maxLength, $(this).val().length, minLength);
    };
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
    if (typeof (forPicker) === "undefined") {
        forPicker = true;
    }
    var formattedDate = $.datepicker.formatDate("mm/dd/yy", date);
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
                    requestInstructionsDiv.fadeIn();
                    // if the form is for agency users then collapse the panel by default, else expand the panel
                    if ($(".new-request-agency").length === 1) {
                        $("#collapse-agency-instructions").collapse("hide");
                    } else {
                        $("#collapse-agency-instructions").collapse("show");
                    }
                } else {
                    requestInstructionsDiv.fadeOut();
                }
            },
            error: function () {
                requestInstructionsDiv.fadeOut();
            }
        });
    } else {
        requestInstructionsDiv.fadeOut();
    }
}

// handle text change for agency instruction panel title
$('#collapse-agency-instructions').on('shown.bs.collapse', function () {
    $('#agency-instructions-title-text').html("<span class=\"glyphicon glyphicon-chevron-up\"></span>&nbsp;&nbsp;Hide Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-up\"></span>");
});

$('#collapse-agency-instructions').on('hidden.bs.collapse', function () {
    $('#agency-instructions-title-text').html("<span class=\"glyphicon glyphicon-chevron-down\"></span>&nbsp;&nbsp;Show Agency Instructions&nbsp;&nbsp;<span class=\"glyphicon glyphicon-chevron-down\"></span>");
});

// variables used to handle custom forms
var customRequestFormsEnabled = false; // determines if custom request forms have been enabled
var showMultipleRequestTypes = false; // determines if that agency's custom forms can be repeated
var repeatableCounter = {}; // tracks how many more repeatable options can be rendered
var maxRepeatable = {}; // tracks the maximum number of times each form can be repeated
var previousValues = []; // tracks the previous values of each request type dropdown
var currentValues = []; // tracks the current values of each request type dropdown
var customRequestFormCounter = 1; // tracks how many request type dropdowns have been rendered
var dismissTarget = ""; // tracks which dismiss button is being clicked
var customRequestFormData = {}; // tracks the data of custom forms that will be sent on submit
var formCategories = {}; // tracks what category each form belongs to
var categorized = false; // determines if selected agency has categorized forms
var currentCategory = ""; // tracks the current category that can be submitted for the selected agency
var categorySelected = false; // a flag that determines if a category has been set yet or not
var categoryDividerText = "────────────────────";
var defaultInfoText = "Note: The request details written here will not be visible to the public. However, this agency may post a description of the records provided.";
var defaultCateogryInfoText = "This agency has categorized the different types of requests a user can submit and they are separated in the dropdown below. This request may have multiple submissions of only one category.";
var defaultCategoryWarningText = "Selecting this option will remove any existing information for other request types. Are you sure you want to change categories?";
var currentAgency = ""; // tracks the current agency that has been selected
var originalFormNames = {}; // tracks the original text for a form option
var minimumRequired = {}; // tracks the minimum amount of completed fields a custom request forms needs to be submitted

function getCustomRequestForms(agencyEin) {
    /* exported getCustomRequestForms
     *
     * function to determine if custom request forms need to be shown on category or agency change
     */
    if (agencyEin === "") {
        $("#custom-request-panel-1").fadeOut();
        $("#request-description").val("");
        $("#request-description-section").fadeIn();
        return;
    }

    customRequestFormsEnabled = false;
    repeatableCounter = {};
    categorized = false;
    maxRepeatable = {};
    formCategories = {};
    currentCategory = "";
    categorySelected = false;
    customRequestFormCounter = 1;
    currentAgency = agencyEin;

    var selectedAgency = agencyEin;
    var customRequestPanelDiv = $("#custom-request-panel-" + customRequestFormCounter.toString());
    var customRequestFormsDivId = "#custom-request-forms-" + customRequestFormCounter.toString();
    var requestTypeId = "#request-type-" + customRequestFormCounter.toString();
    var customRequestFormId = "#custom-request-form-content-" + customRequestFormCounter.toString();
    var customRequestFormsDiv = $(customRequestFormsDivId);
    var requestType = $(requestTypeId);
    var customRequestFormContent = $(customRequestFormId);
    var customRequestFormAdditionalContent = $("#custom-request-form-additional-content");
    var requestDescriptionSection = $("#request-description-section");
    var requestDescriptionField = $("#request-description");

    requestType.empty();
    customRequestFormContent.html("");
    customRequestFormContent.hide();
    customRequestFormAdditionalContent.hide();
    $("#custom-request-forms-warning").hide();

    // ajax call to show request type drop down
    $.ajax({
        url: "/agency/feature/" + selectedAgency + "/" + "custom_request_forms",
        type: "GET",
        success: function (data) {
            if (data["custom_request_forms"]["enabled"] === true) {
                // determine if form options are categorized
                if (data["custom_request_forms"]["categorized"]) {
                    categorized = true;
                    // set custom text is agency has provided it otherwise use the default text
                    if (data["custom_request_forms"]["category_info_text"]) {
                        $("#request-info-text").html(defaultInfoText.bold() + " " + data["custom_request_forms"]["category_info_text"].bold());
                    } else {
                        $("#request-info-text").html(defaultInfoText.bold() + " " + defaultCateogryInfoText.bold());
                    }
                    if (data["custom_request_forms"]["category_warning_text"]) {
                        $("#category-warning-text").html(data["custom_request_forms"]["category_warning_text"]);
                    } else {
                        $("#category-warning-text").html(defaultCategoryWarningText);
                    }
                    $("#category-info").show();
                } else {
                    categorized = false;
                    $("#category-info").hide();
                }
                customRequestFormsEnabled = true;
                // hide request description and pre fill it with placeholder to bypass parsley
                requestDescriptionSection.hide();
                requestDescriptionField.val("custom request forms");
                // ajax call to populate request type drop down with custom request form options
                $.ajax({
                    url: "/agency/api/v1.0/custom_request_forms/" + selectedAgency,
                    type: "GET",
                    success: function (data) {
                        if (data.length === 1) {
                            originalFormNames[data[0][0]] = data[0][1];
                            repeatableCounter[[data[0][0]]] = data[0][2];
                            maxRepeatable[[data[0][0]]] = data[0][2];
                            formCategories[[data[0][0]]] = data[0][3];
                            minimumRequired[[data[0][0]]] = data[0][4];
                            requestType.append(new Option(data[0][1], data[0][0]));
                            previousValues[0] = "";
                            currentValues[0] = "";
                            customRequestPanelDiv.fadeIn();
                            customRequestFormsDiv.fadeIn();
                            renderCustomRequestForm("1"); // render the form to the first custom request form content div
                            if (moreOptions()) {
                                customRequestFormAdditionalContent.fadeIn();
                            }
                        } else {
                            var categoryCounter = 1;
                            requestType.append(new Option("", ""));
                            for (var i = 0; i < data.length; i++) {
                                originalFormNames[data[i][0]] = data[i][1];
                                repeatableCounter[data[i][0]] = data[i][2]; // set the keys to be the form id
                                maxRepeatable[[data[i][0]]] = data[i][2];
                                formCategories[data[i][0]] = data[i][3];
                                minimumRequired[data[i][0]] = data[i][4];
                                var option = new Option(data[i][1], data[i][0]);
                                // append a divider after the last form in a category
                                if (data[i][3] !== categoryCounter && categorized) {
                                    var optionDivider = new Option(categoryDividerText);
                                    optionDivider.disabled = true;
                                    requestType.append(optionDivider); // append a disabled divider option
                                    categoryCounter++;
                                }
                                requestType.append(option);
                            }
                            previousValues[0] = "";
                            currentValues[0] = "";

                            customRequestPanelDiv.fadeIn();
                            customRequestFormsDiv.fadeIn();
                        }
                        updateCustomRequestFormDropdowns();
                    }
                });
                // check if custom forms are repeatable
                if (data["custom_request_forms"]["multiple_request_types"] === true) {
                    showMultipleRequestTypes = true;
                } else {
                    showMultipleRequestTypes = false;
                }
            } else {
                customRequestPanelDiv.hide();
                customRequestFormsDiv.hide();
                $("#category-info").hide();
                // if custom request forms are disabled then show the regular request description
                requestDescriptionSection.show();
                requestDescriptionField.val("");
            }
        },
        error: function () {
            customRequestPanelDiv.hide();
            customRequestFormsDiv.hide();
            $("#category-info").hide();
            requestDescriptionSection.show();
            requestDescriptionField.val("");
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
    var customRequestFormAdditionalContent = $("#custom-request-form-additional-content");

    $(".request-type").each(function () {
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
                    } else {
                        var categoryCounter = 1;
                        requestType.append(new Option("", ""));
                        for (var i = 0; i < data.length; i++) {
                            var option = new Option(data[i][1], data[i][0]);
                            if (data[i][3] !== categoryCounter && categorized) {
                                var optionDivider = new Option(categoryDividerText);
                                optionDivider.disabled = true;
                                requestType.append(optionDivider);
                                categoryCounter++;
                            }
                            if (repeatableCounter[data[i][0]] === 0) {
                                // if all possible instances of the form have been rendered then disable the option
                                option.disabled = true;
                            }
                            requestType.append(option);
                        }
                    }
                    updateCustomRequestFormDropdowns();
                }
            });
        }
    });
}

function updateCustomRequestFormDropdowns() {
    /*
     * Update the dropdowns to disable options where they are no longer repeatable.
     * Update the option text to show instance number of each form and how many more you can create.
     */
    // this section handles disabling options when they reach their repeatable limit
    $(".request-type").each(function () {
        var requestTypeOptions = "#" + this.id + " > option";
        $(requestTypeOptions).each(function () {
            if (repeatableCounter[this.value] === 0 || this.value === categoryDividerText) {
                $(this).attr("disabled", "disabled");
            } else {
                $(this).removeAttr("disabled");
            }
        });
    });

    // this section dynamically updates the option text to show how many more times a form can be created
    var backwards = {}; // we will use this to count backwards from the number of form instances used until we reach 0
    var originalBackwards = {}; // this keeps track of original number of instances of each form before we started counting backwards

    // set the counters to have 0 for each form id
    for (var key in repeatableCounter) {
        backwards[key] = 0;
        originalBackwards[key] = 0;
    }
    // loop through currentValues and every time you see an instance of a form id, increment the counter
    for (var i = 0; i < currentValues.length; i++) {
        backwards[currentValues[i]]++;
        originalBackwards[currentValues[i]]++;
    }

    // now we have counters that tell us how many times a form id appears on screen

    // loop through each request type dropdown
    $(".request-type").each(function () {
        var requestTypeOptions = "#" + this.id + " > option";
        if (this.value !== "") { // if the dropdown is not empty execute this block
            $(requestTypeOptions).each(function () { // loop through each option in the dropdown
                if (this.text !== "" && this.text !== categoryDividerText) { // only update options that actually have text
                    var originalText = originalFormNames[this.value]; // get the actual form name
                    if (backwards[this.value] === 0) { // if there are no instances of the form keep the text at 0
                        if (showMultipleRequestTypes) {
                            $(this).text(originalText + " (" + (backwards[this.value]).toString() + " of " + maxRepeatable[this.value].toString() + ")");
                        } else {
                            $(this).text(originalText);
                        }
                    } else { // use the following formula, maxRepeatable[this.value] - backwards[this.value] - repeatableCounter[this.value] + 1 to calculate what instance number is currently being processed
                        if (showMultipleRequestTypes) {
                            $(this).text(originalText + " (" + (maxRepeatable[this.value] - backwards[this.value] - repeatableCounter[this.value] + 1).toString() + " of " + maxRepeatable[this.value].toString() + ")");
                        } else { // use original text if only one custom form can display
                            $(this).text(originalText);
                        }
                    }
                    if (backwards[this.value] > 1) { // update the backwards counter for the next time you see the same form selected in another dropdown
                        backwards[this.value]--;
                    }
                }
            });
        } else { // if the dropdown is empty execute this block because we have to skip this when counting backwards
            $(requestTypeOptions).each(function () {
                if (this.text !== "" && this.text !== categoryDividerText) {
                    // if we see a dropdown with no value selected then we will use the original instance counter number to prepare for when an option is actually selected
                    var originalText = originalFormNames[this.value];
                    if (showMultipleRequestTypes) {
                        $(this).text(originalText + " (" + (originalBackwards[this.value]).toString() + " of " + maxRepeatable[this.value].toString() + ")");
                    } else {
                        $(this).text(originalText);
                    }
                }
            });
        }
    });
}

function disableOptions() {
    /*
     * Update the dropdowns to disable all options that don't belong to the current category
     */
    $(".request-type").each(function () {
        var requestTypeOptions = "#" + this.id + " > option";
        $(requestTypeOptions).each(function () {
            if (formCategories[this.value] !== currentCategory && this.value !== "") {
                $(this).attr("disabled", "disabled");
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
                currentValues[target - 1] = formId;

                detectChange(); // determine which request type dropdown was changed

                customRequestFormContent.html(data["form_template"]);
                previousValues[target - 1] = formId;
                updateCustomRequestFormDropdowns();
                if (categorized) {
                    currentCategory = formCategories[formId];
                }

                try {
                    // render datepicker plugins
                    $(".custom-request-form-datepicker").datepicker({
                        dateFormat: "mm/dd/yy"
                    }).mask("99/99/9999");

                    // render datepicker plugins where past date is allowed
                    $(".datepicker-past-only").datepicker({
                        dateFormat: "mm/dd/yy",
                        maxDate: 0
                    }).mask("99/99/9999");

                    // render datepicker plugins where future date is allowed
                    $(".datepicker-future-only").datepicker({
                        dateFormat: "mm/dd/yy",
                        minDate: 0
                    }).mask("99/99/9999");
                } catch (err) {
                    // if one of the forms doesn't have a date field it will throw an error when you try to render it
                    // TODO: find a better way to handle this error
                }

                try {
                    // render timepicker plugins
                    $(".timepicker").timepicker({
                        timeFormat: "h:mm p",
                        interval: 15,
                        minTime: "12:00am",
                        maxTime: "11:59pm",
                        startTime: "12:00am",
                        dynamic: false,
                        dropdown: true,
                        scrollbar: true
                    }).keydown(function (e) {
                        // prevent keyboard input except for allowed keys
                        if (e.keyCode !== 8 && // backspace
                            e.keyCode !== 9 && // tab
                            e.keyCode !== 37 && // left-arrow
                            e.keyCode !== 39 && // right-arrow
                            e.keyCode !== 48 && // 0
                            e.keyCode !== 49 && // 1
                            e.keyCode !== 50 && // 2
                            e.keyCode !== 51 && // 3
                            e.keyCode !== 52 && // 4
                            e.keyCode !== 53 && // 5
                            e.keyCode !== 54 && // 6
                            e.keyCode !== 55 && // 7
                            e.keyCode !== 56 && // 8
                            e.keyCode !== 57 && // 9
                            e.keyCode !== 96 && // num pad 0
                            e.keyCode !== 97 && // num pad 1
                            e.keyCode !== 98 && // num pad 2
                            e.keyCode !== 99 && // num pad 3
                            e.keyCode !== 100 && // num pad 4
                            e.keyCode !== 101 && // num pad 5
                            e.keyCode !== 102 && // num pad 6
                            e.keyCode !== 103 && // num pad 7
                            e.keyCode !== 104 && // num pad 8
                            e.keyCode !== 105 && // num pad 9
                            e.keyCode !== 16 && // Shift
                            e.keyCode !== 65 && // a
                            e.keyCode !== 77 && // m
                            e.keyCode !== 80 && // p
                            e.keyCode !== 186) {// semi-colon
                            e.preventDefault();
                        }
                    });

                } catch (err) {
                    // if one of the forms doesn't have a time field it will throw an error when you try to render it
                    // TODO: find a better way to handle this error
                }

                // initialize character counters in custom forms
                for (var id in data["character_counters"]) {
                    $("#" + id).keyup(
                        generateCharacterCounterHandler(id, data["character_counters"][id]["max_length"], data["character_counters"][id]["min_length"])
                    );
                }

                // initialize popovers in custom forms
                for (var id in data["popovers"]) {
                    $("#" + id).attr({
                        'data-placement': "top",
                        'data-trigger': "hover focus",
                        'data-toggle': "popover",
                        'data-content': data["popovers"][id]["content"],
                        title: data["popovers"][id]["title"]
                    });
                    $("#" + id).popover();
                }

                // initialize tooltips in custom forms
                for (var id in data["tooltips"]) {
                    $("#" + id + "-tooltip").attr({
                        'data-placement': "right",
                        'data-trigger': "hover focus",
                        'data-toggle': "popover",
                        'data-content': data["tooltips"][id]["content"],
                        'aria-label': data["tooltips"][id]["content"],
                        title: data["tooltips"][id]["title"]
                    });
                    $("#" + id + "-tooltip").popover();
                }

                // Do not reset on click
                $(".select-multiple").find("option").mousedown(function (e) {
                    e.preventDefault();
                    $(".select-multiple").focus();
                    $(this).prop("selected", !$(this).prop("selected"));
                    return false;
                });

                // Set custom validation messages
                for (var id in data["error_messages"]) {
                    $("#" + id).attr("data-parsley-required-message", data["error_messages"][id]);
                }

                customRequestFormContent.show();
                // check to show add new request information button
                if (showMultipleRequestTypes === true) {
                    // check if repeatable counter still has options
                    if (moreOptions()) {
                        customRequestFormAdditionalContent.show();
                    } else {
                        customRequestFormAdditionalContent.hide();
                    }
                } else {
                    customRequestFormAdditionalContent.hide();
                }
            }
        });
    } else {
        customRequestFormContent.html("");
        customRequestFormContent.hide();
        customRequestFormAdditionalContent.hide();

        // update the values in the tracking variables
        currentValues[target - 1] = "";

        detectChange();

        previousValues[target - 1] = "";
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
    if (currentValues[targetId - 1] !== "") {
        repeatableCounter[currentValues[targetId - 1]] = repeatableCounter[currentValues[targetId - 1]] + 1;
        previousValues[targetId - 1] = "";
        currentValues[targetId - 1] = "";
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

function handleCategorySwitch(formId) {
    /*
     * handle a category switch by removing all appended divs,
      * set the new currentCategory,
      * and render a new form belonging to the new category to the first custom request form panel.
     */
    $(".appended-div").remove();
    // reset the current and previous value arrays
    for (var i = 0; i < currentValues.length; i++) {
        previousValues[i] = "";
        currentValues[i] = "";
    }
    currentValues[0] = formId;
    // reset the repeatable counter using ajax
    $.ajax({
        url: "/agency/api/v1.0/custom_request_forms/" + currentAgency,
        type: "GET",
        success: function (data) {
            for (var i = 0; i < data.length; i++) {
                repeatableCounter[data[i][0]] = data[i][2]; // set the keys to be the form id
            }
        }
    });
    currentCategory = formCategories[formId];
    // set the new form to the first dropdown and render it
    $("#request-type-1").val(formId);
    renderCustomRequestForm("1");
}

function checkRequestTypeDropdowns() {
    /*
     * Function to check if at least one request type dropdown has a selected value
     */
    $("#custom-request-forms-warning").hide();
    var counter = 0;
    for (var i = 0; i < currentValues.length; i++) {
        if (currentValues[i] !== "") {
            counter++;
        }
    }
    if (customRequestFormsEnabled === true && counter === 0) {
        $("#custom-request-forms-warning").show();
        return true;
    }
    return false;
}

function processCustomRequestFormData() {
    /*
     * Process the custom request form data into a JSON to be passed back on submit
     */
    var formNumber = 1;
    var fieldNumber = 1;
    var invalidForms = [];
    var requestDescriptionText = "";
    for (var i = 0; i < currentValues.length; i++) {
        if (currentValues[i] !== "") {
            var target = (i + 1).toString();
            var formKey = "form_";
            var fieldKey = "field_";
            var formId = $("#request-type-" + target + " option:selected").val();
            var formName = originalFormNames[formId];
            var previousRadioId = "";
            var completedFields = 0;

            // add leading zero to forms less than 10 so they can be properly sorted
            if (formNumber < 10) {
                formKey = formKey + "0" + formNumber;
            } else {
                formKey = formKey + formNumber;
            }

            customRequestFormData[formKey] = {};
            customRequestFormData[formKey]["form_name"] = formName;
            customRequestFormData[formKey]["form_fields"] = {};

            // append form name to request description text
            requestDescriptionText = requestDescriptionText + formName + ", ";

            // loop through each form field to get the value
            $("#custom-request-form-content-" + target + " > .custom-request-form-field > .custom-request-form-data").each(function () {
                var fieldName = $("label[for='" + this.id + "']").html();
                fieldName = fieldName.replace(" (required)", "");
                // add leading zero to fields less than 10 so they can be properly sorted
                if (fieldNumber < 10) {
                    fieldKey = fieldKey + "0" + fieldNumber;
                } else {
                    fieldKey = fieldKey + fieldNumber;
                }
                customRequestFormData[formKey]["form_fields"][fieldKey] = {};
                customRequestFormData[formKey]["form_fields"][fieldKey]["field_name"] = fieldName;

                if ($("#" + this.id).prop("multiple") === true) {
                    var selectMultipleId = "#" + this.id;
                    var selectMultipleValue = $(selectMultipleId).val();
                    // set select multiple with no value to empty string so that field_value key is still created
                    if (selectMultipleValue == null) {
                        selectMultipleValue = "";
                    }
                    customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = selectMultipleValue;
                    if (selectMultipleValue !== "") {
                        completedFields++;
                    }

                } else if ($("#" + this.id).is(":radio") === true) {
                    // since all radio inputs have the same id only take the value of the first one to avoid duplicates
                    var radioValue = $("input[name='" + this.id + "']:checked").val();
                    // set radios with no value to empty string so that field_value key is still created
                    if (radioValue == null) {
                        radioValue = "";
                    }
                    if (this.id !== previousRadioId) {
                        customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = radioValue;
                        if (radioValue !== "") {
                            completedFields++;
                        }
                    } else {
                        fieldNumber--;
                    }
                    previousRadioId = this.id;
                } else {
                    customRequestFormData[formKey]["form_fields"][fieldKey]["field_value"] = this.value;
                    if (this.value !== "") {
                        completedFields++;
                    }
                }
                fieldNumber++;
                fieldKey = "field_";
            });
            if (completedFields < minimumRequired[currentValues[i]]) {
                var invalidFormContent = "#custom-request-form-content-" + target;
                var invalidForm = "#custom-request-forms-" + target;
                var invalidFormErrorDiv = invalidForm + "-error-div";
                if (minimumRequired[currentValues[i]] > 1) {
                    $(invalidFormContent).prepend("<div class='alert alert-danger remove-on-resubmit' id='" + invalidFormErrorDiv + "'>You need to fill in at least " + minimumRequired[currentValues[i]] + " fields to submit this form.</div>");
                } else {
                    $(invalidFormContent).prepend("<div class='alert alert-danger remove-on-resubmit' id='" + invalidFormErrorDiv + "'>You need to fill in at least " + minimumRequired[currentValues[i]] + " field to submit this form.</div>");
                }
                invalidForms.push(invalidForm);
            }

            completedFields = 0;
            formNumber++;
            fieldNumber = 1;
        }
    }
    $("#custom-request-forms-data").val(JSON.stringify(customRequestFormData));
    if (customRequestFormsEnabled) {
        requestDescriptionText = requestDescriptionText.slice(0, -2); // remove the last 2 characters
        $("#request-description").val(requestDescriptionText);
    }
    return invalidForms;
}

/**
 * Check for the presence of a SSN in a string.
 * @param {string} text
 * @returns {boolean} Whether the string contains an SSN
 */
function checkSSN(text) {
    var ssnPattern = /[0-9]{3}[\-\.\s]?[0-9]{2}[\-\.\s]?[0-9]{4}/;
    return ssnPattern.test(text);
}

/**
 * Cancel form submission if user chooses to review Title and / or Description.
 */
function handlePIIModalReview(){
    $('#processing-submission').hide();
    $('#submit').show();
    $(window).scrollTop($('#request-title').offset().top - 50);
    showPIIWarning = true;
    return;
}