"use strict";

$(function () {

    // set time zone name
    $("input[name='tz_name']").val(jstz.determine().name());

    var start = 0,
        end = 0,
        total = 0,
        canSearch = true,
        toFocus = false,
        searchBtn = $("#search"),
        searchBtnAdv = $("#search-adv"),
        clearSearchBtn = $("#clearsearch"),
        dateSubmittedReq = $("#date-submitted-req"),
        dateDueReq = $("#date-due-req"),
        dateClosedReq = $("#date-closed-req"),
        noResultsFound = true,
        generateDocBtn = $("#generate-document"),
        agencySelect = $("#agency_ein"),
        agencyUserDiv = $("#agency-user-div"),
        agencyUserSelect = $("#agency_user"),
        requestType = $("#request_type"),
        resultsHeader = "resultsHeading",
        isAgencyUser = ($("#is-agency-user").val() === "true"),
        resultcol = [];

    // Table head values
    if (isAgencyUser) {
        resultcol = [
            ["Status", ""],
            ["ID", ""],
            ["Date Submitted", "sort_date_submitted", "desc"],
            ["Title", "sort_title", "none"],
            ["Assigned Agency", ""],
            ["Date Due", "sort_date_due", "none"],
            ["Date Closed", ""],
            ["Requester Name", ""]
        ];

        var userAgencies = [];
        $("#user-agencies option").each(function () {
            userAgencies.push($(this).val());
        });
    } else {
        resultcol = [
            ["Status", ""],
            ["ID", ""],
            ["Date Submitted", "sort_date_submitted", "desc"],
            ["Title", "sort_title", "none"],
            ["Assigned Agency", ""],
            ["Date Due", "sort_date_due", "none"]
        ];
    }
    var sortSequence = ["none", "desc", "asc"];

    // Date stuff
    function dateInvalid(dateElem, msg, highlightDateRequirement, dateError) {
        dateElem
            .addClass("bad-input-text")
            .attr('data-content', msg)
            .popover(msg === null ? 'hide' : 'show');
        if (highlightDateRequirement) {
            dateError.css("display", "block");
            dateError.focus();
        }
        return false;
    }

    function dateValid(dateElem) {
        dateElem
            .removeClass("bad-input-text")
            .popover('hide');
        return true;
    }

    function valiDate(checkDateElem, compDateElem, isLessThan, dateError) {
        /*
        * Check that 'checkDateElem' holds an empty value or
        * that it is not a holiday or weekend and
        * that it 'isLessThan' (or greater than if 'isLessThan' == false)
        * compDateElem and style accordingly.
        * */
        if (checkDateElem.val()) {
            if (checkDateElem.val().length === 10) {
                var compDate = null;
                if (compDateElem.val().length === 10) {
                    try {
                        compDate = new Date(compDateElem.val());
                    } catch (err) {
                        compDate = null;
                    }
                }
                try {
                    var checkDate = new Date(checkDateElem.val());
                    var validComp = compDate !== null ?
                        (isLessThan ? checkDate <= compDate : checkDate >= compDate) : true;
                    if (!notHolidayOrWeekend(checkDate, false)) {
                        return dateInvalid(checkDateElem, "This date does not fall on a business day.", null, dateError);
                    } else if (!validComp) {
                        return dateInvalid(checkDateElem, null, true, dateError);
                    } else {
                        return dateValid(checkDateElem);
                    }
                } catch (err) {
                    // failure parsing date string
                    return dateInvalid(checkDateElem, "This is not a valid date.", null, dateError);
                }
            } else {
                // missing full date string length
                return dateInvalid(checkDateElem, "This is not a valid date.", null, dateError);
            }
        } else {
            // empty value is valid (no filtering)
            return dateValid(checkDateElem);
        }
    }

    function valiDates(fromDateElem, toDateElem, dateError) {
        /*
        * Check that 'fromDateElem' is less than 'toDateElem'
        * and that both dates are not holidays or weekends.
        * */
        var fromValid = valiDate(fromDateElem, toDateElem, true, dateError),
            toValid = valiDate(toDateElem, fromDateElem, false, dateError);
        if (!fromValid || !toValid) {
            canSearch = false;
            searchBtn.attr("disabled", true);
            searchBtnAdv.attr("disabled", true);
            generateDocBtn.attr("disabled", true);
        } else {
            canSearch = true;
            searchBtn.attr("disabled", false);
            searchBtnAdv.attr("disabled", false);
            dateError.css("display", "none");
            if (!noResultsFound) {
                generateDocBtn.attr("disabled", false);
            }
        }
    }

    var datepickerOptions = {
        dateFormat: "mm/dd/yy",
        daysOfWeekDisabled: [0, 6],
        beforeShowDay: notHolidayOrWeekend,
    };

    var dateRecFromElem = $("#date-rec-from");
    var dateRecToElem = $("#date-rec-to");
    var dateDueFromElem = $("#date-due-from");
    var dateDueToElem = $("#date-due-to");
    var dateClosedFromElem = $("#date-closed-from");
    var dateClosedToElem = $("#date-closed-to");

    var dates = [dateRecFromElem, dateRecToElem, dateDueFromElem, dateDueToElem, dateClosedFromElem, dateClosedToElem];
    for (var i = 0; i < dates.length; i++) {
        dates[i].datepicker(datepickerOptions);
        dates[i].mask("00/00/0000", {placeholder: "mm/dd/yyyy"});
    }
    dateRecFromElem.on("input change", function () {
        valiDates(dateRecFromElem, dateRecToElem, dateSubmittedReq);
    });
    dateRecToElem.on("input change", function () {
        valiDates(dateRecFromElem, dateRecToElem, dateSubmittedReq);
    });
    dateDueFromElem.on("input change", function () {
        valiDates(dateDueFromElem, dateDueToElem, dateDueReq);
    });
    dateDueToElem.on("input change", function () {
        valiDates(dateDueFromElem, dateDueToElem, dateDueReq);
    });
    dateClosedFromElem.on("input change", function () {
        valiDates(dateClosedFromElem, dateClosedToElem, dateClosedReq);
    });
    dateClosedToElem.on("input change", function () {
        valiDates(dateClosedFromElem, dateClosedToElem, dateClosedReq);
    });

    // keypress 'Enter' = click search button
    $("#search-section").keyup(function (e) {
        if (canSearch && e.keyCode === 13) {
            searchBtn.click();
        }
    });
    // but don't submit form (it is only used to generate results document)
    $("#search-form").on("keyup, keypress", function (e) {
        var keyCode = e.keyCode || e.which;
        if (keyCode === 13) {
            e.preventDefault();
            searchBtn.click();
        }
    });

    // Capture form reset
    $(clearSearchBtn).on('click', function (event) {
        event.preventDefault();
        $("#search-form")[0].reset();

        // Need to do some self clean up
        var query = $("#query");
        var names = ["title", "description", "agency_request_summary", "requester_name"];
        var i;

        query.attr("placeholder", "Enter keywords");
        for (i = 0; i < names.length; i++) {
            $("input[name='" + names[i] + "']").prop("disabled", false);
            $("input[name='" + names[i] + "']").removeClass("disabled");
        }

        // re enable search buttons and hide date error
        searchBtn.attr("disabled", false);
        searchBtnAdv.attr("disabled", false);
        dateSubmittedReq.hide();
        dateDueReq.hide();
        dateClosedReq.hide();

        $(query).focus();
        resetAndSearch();
    });

    // show test info
    // document.onkeypress = function (e) {
    //     var testInfo = $(".test-info");
    //     if (e.keyCode === 92) {
    //         if (testInfo.is(":visible")) {
    //             testInfo.hide();
    //         }
    //         else {
    //             testInfo.show();
    //         }
    //     }
    // };

    function buildResultsTableHead(col, sort) {
        var tableHead = "";

        for (var i = 0; i < col.length; i++) {
            if (col[i][1] === "") {
                tableHead = tableHead + "<th>" + col[i][0] + "</th>";
            } else {
                tableHead = tableHead + '<th><button type="button" class="sort-field" data-sort-order="' + col[i][2] + '" id="' + col[i][1] + '">' + col[i][0];
                var CurrentSort = $("input[name=" + col[i][1] + "]").val();
                if (CurrentSort !== "") {

                }
                tableHead = tableHead + '<span class="glyphicon glyphicon-sort" aria-hidden="true"></span>' +
                    '<span class="sr-only unsorted">Unsorted</span>' +
                    '<span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>' +
                    '<span class="sr-only sorted-asc">Sorted, Ascending</span>' +
                    '<span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>' +
                    '<span class="sr-only sorted-desc">Sorted, Descending</span> </button></th>';
            }
        }
        return tableHead;
    }

    function buildResultsTable(theResults, count, total) {
        var theTable = "";
        theTable = theTable + '<div class="col-sm-12 searchResults-heading">';
        theTable = theTable + '<h2 id="resultsHeading" tabindex="0" aria-live="assertive">Displaying&nbsp;' + (start + 1) + " - " + (start + count) + ' of ' + total.toLocaleString() + '&nbsp;Results Found</h2>';
        theTable = theTable + '<div class="table-legend" aria-hidden="true"><div>Request is:</div>&nbsp;<div class="legend legend-open">Open=<img src="/static/img/open.svg" alt="Open status icon"></div>';
        if (isAgencyUser) {
            theTable = theTable + '<div class="legend legend-progress">In Progress=<img src="/static/img/progress.svg" alt="In progress status icon"></div>';
            theTable = theTable + '<div class="legend legend-soon">Due Soon=<img src="/static/img/soon.svg" alt="Due soon status icon"></div>';
            theTable = theTable + '<div class="legend legend-overdue">Overdue=<img src="/static/img/overdue.svg" alt="Overdue status icon"></div>';
        }
        theTable = theTable + '<div class="legend legend-closed">Closed=<img src="/static/img/closed.svg" alt="Closed status icon"></div>';
        theTable = theTable + '</div>';
        theTable = theTable + '<div class="alert alert-info col-md-12" tabindex="0"><strong>*</strong> - "Under Review" means the request was recently submitted and the agency has 5 business days to review the request for personal identifying information before it becomes publicly viewable.</div>';
        theTable = theTable + '<div class="table table-responsive"><table class="table table-striped"><thead>';
        theTable = theTable + buildResultsTableHead(resultcol, sortSequence);
        theTable = theTable + '</thead><tbody>' + theResults + '</tbody></table></div>';
        return theTable;
    }

    var next = $("#next");
    var prev = $("#prev");

    function search() {
        // first clear out any "bad" input
        $(".bad-input-text").removeClass("bad-input-text").val("");

        var results = $("#results");
        var pageInfo = $("#page-info");
        results.html('<div class="col-sm-12 search-load-container"> <div class="search-loader"><span class="sr-only">Loading the results...</span></div></div>');

        $.ajax({
            url: "/search/requests",
            data: $("#search-form").serializeArray(),
            success: function (data) {
                if (data.total !== 0) {
                    noResultsFound = false;
                    results.html(buildResultsTable(data.results, data.count, data.total.value));
                    flask_moment_render_all();
                    $(".pagination").css("display", "flex");
                    pageInfo.text(
                        (start + 1) + " - " +
                        (start + data.count) +
                        " of " + (data.total.value).toLocaleString()
                    );
                    total = data.total.value;
                    end = start + data.count;
                    if (end === total) {
                        next.attr("aria-disabled", true);
                        next.addClass("disabled")
                    } else {
                        next.attr("aria-disabled", false);
                        next.removeClass("disabled")
                    }
                    if (start === 0) {
                        prev.attr("aria-disabled", true);
                        prev.addClass("disabled")
                    } else {
                        prev.attr("aria-disabled", false);
                        prev.removeClass("disabled")
                    }
                    generateDocBtn.attr("disabled", false);

                    if (toFocus) {
                        scrollToElement(resultsHeader);
                        toFocus = false;
                    }
                } else {
                    noResultsFound = true;
                    results.html("<div class='row'><div class='col-sm-12 errorResults'>" +
                        "<p class='text-center' aria-live='polite'>No results found.</p></div></div>");
                    generateDocBtn.attr("disabled", true);
                }
            },
            error: function (e) {
                results.html("<div class='row'><div class='col-sm-12 errorResults'>" +
                    "<p class='text-center' aria-live='assertive'>Hmmmm.... Looks like something's gone wrong.</p></div></div>");
                generateDocBtn.attr("disabled", true);
            }
        });
    }

    // search on load
    $(document).ready(function () {
        search();
    });

    // disable other filters if searching by FOIL-ID
    $("input[name='foil_id']").click(function () {
        var query = $("#query");
        var names = ["title", "description", "agency_request_summary", "requester_name"];
        var i;
        if ($(this).prop("checked")) {
            query.attr("placeholder", "0000-000-00000");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", true);
                $("input[name='" + names[i] + "']").addClass("disabled");
            }
        } else {
            query.attr("placeholder", "Enter keywords");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", false);
                $("input[name='" + names[i] + "']").removeClass("disabled");
            }
        }
    });

    function setStart(val) {
        start = val;
        $("input[name='start']").val(val);
    }

    // Sorting
    function updateSorting(theHeadingId, sequence) {

        for (var i = 0; i < resultcol.length; i++) {

            if (resultcol[i][1] === theHeadingId) {
                resultcol[i][2] = sequence;
            }
        }
    }

    function cycleSort(elem) {
        /*
        * Cycle through sortSequence and 'style' elem with arrows
        * glyphicons representing sort direction.
        * */

        elem.attr(
            "data-sort-order",
            sortSequence[
            (sortSequence.indexOf(elem.attr("data-sort-order")) + 1 + sortSequence.length)
            % sortSequence.length]);

    }

    function resetAndSearch() {
        if (canSearch) {
            setStart(0);
            search();
        }
    }

    generateDocBtn.click(function () {
        if (canSearch) {
            search();
        }
    });
    $(".status").click(function () {
        resetAndSearch();
    });
    searchBtn.click(function () {
        toFocus = true;
        resetAndSearch();
    });
    searchBtnAdv.click(function () {
        toFocus = true;
        resetAndSearch();
    });
    $("#size").change(function () {
        resetAndSearch();
    });

    agencySelect.change(function () {
        agencyUserSelect.empty();
        requestType.empty();

        if (agencySelect.val()) {
            $.ajax({
                url: "/agency/api/v1.0/active_users/" + agencySelect.val(),
                statusCode: {
                    404: function () {
                        agencyUserDiv.hide();
                    }
                },
                success: function (data) {
                    // Populate users
                    $.each(data.active_users, function () {
                        agencyUserSelect.append($("<option />").val(this[0]).text(this[1]));
                    });

                    // Set selected value for standard agency users
                    if (!data.is_admin) {
                        agencyUserSelect.val(data.active_users[1][0]);
                    }

                    agencyUserDiv.show();
                }
            });

            $.ajax({
                url: "/agency/api/v1.0/request_types/" + agencySelect.val(),
                success: function (data) {
                    // Populate request types
                    $.each(data.request_types, function() {
                        requestType.append($("<option />").val(this[0]).text(this[1]));
                    });
                }
            });

            // search after ajax calls are complete so default values are selected
            resetAndSearch();
        } else {
            agencyUserDiv.is(":visible") && agencyUserDiv.hide();
            resetAndSearch();
        }
    });
    agencyUserSelect.change(function () {
        resetAndSearch();
    });

    requestType.change(function () {
        resetAndSearch();
    });

    next.click(function (event) {
        toFocus = true;
        event.preventDefault();
        if (canSearch && end < total) {
            setStart(start + parseInt($("#size").val()));
            $('html, body').stop();
            search();
        }
    });

    prev.click(function (event) {
        toFocus = true;
        event.preventDefault();
        if (canSearch && start > 0) {
            setStart(start - parseInt($("#size").val()));
            $('html, body').stop();
            search();
        }
    });

    $('body').on('click', '.sort-field', function () {
        if (canSearch) {
            setStart(0);
            cycleSort($(this));

            // fill hidden inputs
            $("input[name='" + $(this).attr("id") + "']").val($(this).attr("data-sort-order"));

            //Update Array to reflect column status
            updateSorting($(this).attr("id"), $(this).attr("data-sort-order"));

            search();
        }
    });

    function scrollToElement(theId) {
        $("#" + theId).focus();
        $('html, body').animate({
            scrollTop: $("#" + theId).offset().top
        }, 500);
    }

    agencySelect.change(function () {
        var selectedAgency = agencySelect.val();
        if (!(userAgencies.includes(selectedAgency)) || selectedAgency === '') {
            $('#redact-results-alert').show();
        } else {
            $('#redact-results-alert').hide();
        }
    });
});
