"use strict";

$(function() {

    // set time zone name
    $("input[name='tz_name']").val(jstz.determine().name());

    var start = 0,
        end = 0,
        total = 0,
        canSearch = true,
        searchBtn = $("#search"),
        searchBtnAdv = $("#search-adv"),
        clearSearchBtn = $("#clearsearch"),
        dateReq = $("#date-req"),
        noResultsFound = true,
        generateDocBtn = $("#generate-document"),
        agencySelect = $("#agency_ein"),
        agencyUserDiv = $("#agency-user-div"),
        agencyUserSelect = $("#agency_user"),
        resultsHeader = "resultsHeading";

    //Table head values
    var resultcol = [
            ['Status',''],
            ['ID',''],
            ['Date Submitted', 'sort_date_submitted','desc'],
            ['Title', 'sort_title','none'],
            ['Assigned Agency', ''],
            ['Date Due','sort_date_due','none']
    ];
    var sortSequence = ["none", "desc", "asc"];

    // Date stuff
    function dateInvalid(dateElem, msg, highlightDateRequirement) {
        dateElem
            .addClass("bad-input-text")
            .attr('data-content', msg)
            .popover(msg === null ? 'hide' : 'show');
        if (highlightDateRequirement) {
            dateReq.css("display", "block");
        }
        return false;
    }

    function dateValid(dateElem) {
        dateElem
            .removeClass("bad-input-text")
            .popover('hide');
        return true;
    }

    function valiDate(checkDateElem, compDateElem, isLessThan) {
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
                    }
                    catch (err) {
                        compDate = null;
                    }
                }
                try {
                    var checkDate = new Date(checkDateElem.val());
                    var validComp = compDate !== null ?
                        (isLessThan ? checkDate <= compDate : checkDate >= compDate) : true;
                    if (!notHolidayOrWeekend(checkDate, false)) {
                        return dateInvalid(checkDateElem, "This date does not fall on a business day.");
                    }
                    else if (!validComp) {
                        return dateInvalid(checkDateElem, null, true);
                    }
                    else {
                        return dateValid(checkDateElem);
                    }
                }
                catch (err) {
                    // failure parsing date string
                    return dateInvalid(checkDateElem, "This is not a valid date.");
                }
            }
            else {
                // missing full date string length
                return dateInvalid(checkDateElem, "This is not a valid date.");
            }
        }
        else {
            // empty value is valid (no filtering)
            return dateValid(checkDateElem);
        }
    }

    function valiDates(fromDateElem, toDateElem) {
        /*
        * Check that 'fromDateElem' is less than 'toDateElem'
        * and that both dates are not holidays or weekends.
        * */
        var fromValid = valiDate(fromDateElem, toDateElem, true),
            toValid = valiDate(toDateElem, fromDateElem, false);
        if (!fromValid || !toValid) {
            canSearch = false;
            searchBtn.attr("disabled", true);
            searchBtnAdv.attr("disabled", true);
            generateDocBtn.attr("disabled", true);
        }
        else {
            canSearch = true;
            searchBtn.attr("disabled", false);
            searchBtnAdv.attr("disabled", false);
            dateReq.css("display", "none");
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
        valiDates(dateRecFromElem, dateRecToElem);
    });
    dateRecToElem.on("input change", function () {
        valiDates(dateRecFromElem, dateRecToElem);
    });
    dateDueFromElem.on("input change", function () {
        valiDates(dateDueFromElem, dateDueToElem);
    });
    dateDueToElem.on("input change", function () {
        valiDates(dateDueFromElem, dateDueToElem);
    });
    dateClosedFromElem.on("input change", function () {
        valiDates(dateClosedFromElem, dateClosedToElem);
    });
    dateClosedToElem.on("input change", function () {
        valiDates(dateClosedFromElem, dateClosedToElem);
    });

    // keypress 'Enter' = click search button
    $("#search-section").keyup(function(e){
        if (canSearch && e.keyCode === 13) {
            searchBtn.click();
            searchBtnAdv.click();
        }
    });
    // but don't submit form (it is only used to generate results document)
    $("#search-form").on("keyup, keypress", function(e){
        var keyCode = e.keyCode || e.which;
        if (keyCode === 13) {
            e.preventDefault();
            searchBtn.click();
        }
    });

    //Capture form reset
    $(clearSearchBtn).on('click', function(event) {
        event.preventDefault();
        $("#search-form")[0].reset();

        //Need to do some self clean up
        var query = $("#query");
        var names = ["title", "description", "agency_request_summary", "requester_name"];
        var i;

        query.attr("placeholder", "Enter keywords");
        for (i = 0; i < names.length; i++) {
            $("input[name='" + names[i] + "']").prop("disabled", false);
        }

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


    function buildResultsTable (theResults, count, total)
    {

        var theTable = "";
        theTable=theTable +'<div class="col-sm-12 searchResults-heading">';
        theTable=theTable + '<h2 id="resultsHeading" tabindex="0" aria-live="assertive">Displaying&nbsp;' + (start + 1) + " - " + (start + count) + ' of ' + total.toLocaleString() + '&nbsp;Results Found</h2>';
        theTable=theTable + '<div class="table-legend" aria-hidden="true"><div>Request is:</div>&nbsp;<div class="legend legend-open">Open=<img src="/static/img/open.svg" > </div><div class="legend legend-closed">Closed=<img src="/static/img/closed.svg" ></div>';
        // Activate for Agency view. A flag is needed to determine if view is active
        // if (agencyView) {
        //     theTable=theTable + '<div class="legend legend-progress">In-progress=<img src="progress.svg" ></div>';
        //     theTable=theTable + '<div class="legend legend-soon">Soon=<img src="soon.svg" ></div>';
        //     theTable=theTable + '<div class="legend legend-overdue">Overdue=<img src="overdue.svg" ></div>';
        // }
        theTable=theTable + '</div></div>';
        theTable=theTable + '<div class="table table-responsive"><table class="table table-striped"><thead>';
        theTable=theTable + buildResultsTableHead (resultcol, sortSequence);
        theTable=theTable + '</thead><tbody>' + theResults + '</tbody></table></div>';
        return(theTable);
    }

    function buildResultsTableHead (col, sort){

        var tableHead = '';

        for (var i=0; i< col.length; i++){

            if (col[i][1] === '')
                {
                tableHead = tableHead + '<th>' + col[i][0] + '</th>';
                }
            else
                {
                tableHead = tableHead + '<th><button type="button" class="sort-field" data-sort-order="' + col[i][2] +'" id="' + col[i][1] +'">' + col[i][0];
                var CurrentSort = $("input[name="+ col[i][1]+ "]").val();
                if (CurrentSort !=""){

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

    var next = $("#next");
    var prev = $("#prev");

    function search() {

        // first clear out any "bad" input
        $(".bad-input-text").removeClass("bad-input-text").val("");

        var results = $("#results");
        var pageInfo = $("#page-info");


        $.ajax({
            url: "/search/requests",
            data: $("#search-form").serializeArray(),
            success: function(data) {
                if (data.total !== 0) {
                    noResultsFound = false;
                    results.html(buildResultsTable(data.results, data.count, data.total));
                    flask_moment_render_all();
                    $(".pagination").css("display", "flex");
                    pageInfo.text(
                        (start + 1) + " - " +
                        (start + data.count) +
                        " of " + (data.total).toLocaleString()
                    );
                    total = data.total;
                    end = start + data.count;
                    if (end === total) {
                        next.attr("aria-disabled", true);
                        next.addClass("disabled")
                    }
                    else {
                        next.attr("aria-disabled", false);
                        next.removeClass("disabled")
                    }
                    if (start === 0) {
                        prev.attr("aria-disabled", true);
                        prev.addClass("disabled")
                    }
                    else {
                        prev.attr("aria-disabled", false);
                        prev.removeClass("disabled")
                    }
                    generateDocBtn.attr("disabled", false);

                }
                else {
                    noResultsFound = true;
                    results.html("<div class='row'><div class='col-sm-12 errorResults'>" +
                          "<p class='text-center' aria-live='polite'>No results found.</p></div></div>");
                    generateDocBtn.attr("disabled", true);
                }
            },
            error: function(e) {
                results.html("<div class='row'><div class='col-sm-12 errorResults'>" +
                    "<p class='text-center' aria-live='assertive'>Hmmmm.... Looks like something's gone wrong.</p></div></div>");
                generateDocBtn.attr("disabled", true);
            }
        });
    }

    // search on load
    $(document).ready(function(){
        search();

    });


    // disable other filters if searching by FOIL-ID
    $("input[name='foil_id']").click(function() {
        var query = $("#query");
        var names = ["title", "description", "agency_request_summary", "requester_name"];
        var i;
        if ($(this).prop("checked")) {
            query.attr("placeholder", "0000-000-00000");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", true);
            }
        }
        else {
            query.attr("placeholder", "Enter keywords");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", false);
            }
        }
    });

    function setStart(val) {
        start = val;
        $("input[name='start']").val(val);
    }

    // Sorting
    function updateSorting(theHeadingId,sequence){

        for (var i=0; i< resultcol.length; i++){

            if (resultcol[i][1] === theHeadingId){
                resultcol[i][2] = sequence;
                // console.log (resultcol[i][2] + "--" + resultcol[i][1]);
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
        resetAndSearch();
        scrollToElement(resultsHeader);

    });
    searchBtnAdv.click(function () {
        resetAndSearch();
        scrollToElement(resultsHeader);


    });
    $("#size").change(function () {
        resetAndSearch();
    });

    agencySelect.change(function () {
        agencyUserSelect.empty();

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
                    $.each(data.active_users ,function() {
                        agencyUserSelect.append($("<option />").val(this[0]).text(this[1]));
                    });

                    // Set selected value for standard agency users
                    if (!data.is_admin) {
                        agencyUserSelect.val(data.active_users[1][0]);
                    }

                    agencyUserDiv.show();
                },
                // search after ajax call is complete so default value for standard user is selected
                complete: function () {
                    resetAndSearch();
                }
            });
        }
        else {
            agencyUserDiv.is(":visible") && agencyUserDiv.hide();
            resetAndSearch();
        }
    });
    agencyUserSelect.change(function () {
        resetAndSearch();
    });
    next.click(function () {
        event.preventDefault();
        if (canSearch && end < total) {
            setStart(start + parseInt($("#size").val()));
            $('html, body').stop();
            search();
            scrollToElement(resultsHeader);
        }


    });
    prev.click(function () {
        event.preventDefault();
        if (canSearch && start > 0) {
            setStart(start - parseInt($("#size").val()));
            $('html, body').stop();
            search();
            scrollToElement(resultsHeader);
        }


    });

    $('body').on('click', '.sort-field', function() {
        if (canSearch) {
            setStart(0);
            cycleSort($(this));

            // fill hidden inputs
            $("input[name='" + $(this).attr("id") + "']").val($(this).attr("data-sort-order"));

            //Update Array to reflect column status
            updateSorting($(this).attr("id"),$(this).attr("data-sort-order"));

           search();
        }
    });

    function scrollToElement(theId){
        $("#"+theId).focus();
        $('html, body').animate({
            scrollTop: $("#"+theId).offset().top
        }, 500);
    }

});
