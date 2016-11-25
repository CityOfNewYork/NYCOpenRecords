$(function() {
    var start = 0;
    var end = 0;
    var total = 0;

    // Date stuff
    function elemToDate(elem) {
        /*
        * Convert an element associated with a date input
        * to a Date object
        * */
        var date = new Date();
        date.setFullYear(parseInt(elem.val().substr(6, 4)));
        date.setMonth(parseInt(elem.val().substr(0, 2)) - 1);
        date.setDate(parseInt(elem.val().substr(3, 2)));
        return date;
    }

    function valiDates(fromDateElem, toDateElem) {
        /*
        * Check that 'fromDateElem' is less than 'toDateElem'
        * and that both dates are not holidays or weekends.
        * */
        valiDate(fromDateElem, toDateElem, true);
        valiDate(toDateElem, fromDateElem, false);
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
                        compDate = elemToDate(compDateElem);
                    }
                    catch (err) {
                        compDate = null;
                    }
                }
                try {
                    var checkDate = elemToDate(checkDateElem);
                    var validComp = compDate !== null ?
                        (isLessThan ? checkDate < compDate : checkDate > compDate) : true;
                    if (!notHolidayOrWeekend(checkDate, false) || !validComp) {
                        checkDateElem.addClass("bad-input-text");
                    }
                    else {
                        checkDateElem.removeClass("bad-input-text");
                    }
                }
                catch (err) {
                    // failure parsing date string
                    checkDateElem.addClass("bad-input-text");
                }
            }
            else {
                // missing full date string length
                checkDateElem.addClass("bad-input-text");
            }
        }
        else {
            // empty value is valid (no filtering)
            checkDateElem.removeClass("bad-input-text");
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

    var dates = [dateRecFromElem, dateRecToElem, dateDueFromElem, dateDueToElem];
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

    // search on load
    search();

    // search on 'Enter'
    $("#search-section").keyup(function(e){
        if(e.keyCode === 13) {
            $("#search").click();
        }
    });

    // TODO: remove after testing
    document.onkeypress = function (e) {
        var testInfo = $(".test-info");
        if (e.keyCode === 92) {
            if (testInfo.is(":visible")) {
                testInfo.hide();
            }
            else {
                testInfo.show();
            }
        }
    };

    var next = $("#next");
    var prev = $("#prev");

    function search() {

        // first clear out any "bad" input
        $(".bad-input-text").removeClass("bad-input-text").val("");

        var results = $("#results");
        var pageInfo = $("#page-info");

        var query = $("#query").val();
        var searchById = $("#foil-id").prop("checked");
        var searchByTitle = $("#title").prop("checked");
        var searchByDescription = $("#description").prop("checked");
        var searchByAgencyDesc = $("#agency-desc").prop("checked");
        var searchByRequesterName = $("#requester-name").prop("checked");
        var dateRecFrom = $("#date-rec-from").val();
        var dateRecTo = $("#date-rec-to").val();
        var dateDueFrom = $("#date-due-from").val();
        var dateDueTo = $("#date-due-to").val();
        var agency = $("#agency").val();
        var statusOpen = $("#open").prop("checked");
        var statusInProg = $("#in-progress").prop("checked");
        var statusClosed = $("#closed").prop("checked");
        var statusDueSoon = $("#due-soon").prop("checked");
        var statusOverdue = $("#overdue").prop("checked");
        var pageSize = $("#size").val();
        var sortDateRec = $("#sort-date-rec").attr("data-sort-order");
        var sortDateDue = $("#sort-date-due").attr("data-sort-order");
        var sortTitle = $("#sort-title").attr("data-sort-order");

        $.ajax({
            url: "/search/requests",
            data: {
                query: query,
                foil_id: searchById,
                title: searchByTitle,
                description: searchByDescription,
                agency_description: searchByAgencyDesc,
                requester_name: searchByRequesterName,
                date_rec_from: dateRecFrom,
                date_rec_to: dateRecTo,
                date_due_from: dateDueFrom,
                date_due_to: dateDueTo,
                agency_ein: agency,
                open: statusOpen,
                closed: statusClosed,
                in_progress: statusInProg,
                due_soon: statusDueSoon,
                overdue: statusOverdue,
                size: pageSize,
                start: start,
                sort_date_submitted: sortDateRec,
                sort_date_due: sortDateDue,
                sort_title: sortTitle
            },
            success: function(data) {
                if (data.total != 0) {
                    results.html(data.results);
                    pageInfo.text(
                        (start + 1) + " - " +
                        (start + data.count) +
                        " of " + data.total
                    );
                    total = data.total;
                    end = start + data.count;
                    if (end === total) {
                        next.hide();
                    }
                    else {
                        next.show();
                    }
                    if (start === 0) {
                        prev.hide();
                    }
                    else {
                        prev.show();
                    }
                }
                else {
                    results.html("<li class='list-group-item text-center'>" +
                        "No results found.</li>");
                    pageInfo.text("");
                    next.hide();
                    prev.hide();
                }
            },
            error: function(e) {
                results.html("<li class='list-group-item text-center'>" +
                    "Hmmmm.... Looks like something's gone wrong.</li>");
                pageInfo.text("");
                next.hide();
                prev.hide();
            }
        });
    }

    // disable other filters if searching by FOIL-ID
    $("#foil-id").click(function() {
        var query = $("#query");
        var ids = ["title", "description", "agency-desc", "requester-name"];
        var i;
        if ($(this).prop("checked")) {
            query.attr("placeholder", "0000-000-00000");
            for (i = 0; i < ids.length; i++) {
                $("#".concat(ids[i])).prop("disabled", true);
            }
        }
        else {
            query.attr("placeholder", "");
            for (i = 0; i < ids.length; i++) {
                $("#".concat(ids[i])).prop("disabled", false);
            }
        }
    });

    $(".status").click(function() {
        start = 0;
        search();
    });
    $("#search").click(function() {
        start = 0;
        search();
    });
    $("#size").change(function() {
        start = 0;
        search();
    });
    $("#agency").change(function() {
        start = 0;
        search();
    });
    next.click(function() {
        if (end < total) {
            start += parseInt($("#size").val());
            search();
        }
    });
    prev.click(function() {
        if (start > 0) {
            start -= parseInt($("#size").val());
            search();
        }
    });

    // Sorting
    var sortOrderToGlyphicon = {
        desc: "glyphicon-triangle-bottom",
        asc: "glyphicon-triangle-top",
        none: "",
    };

    var sortSequence = ["none", "desc", "asc"];

    function cycleSort(elem) {
        /*
        * Cycle through sortSequence and 'style' elem with triangle
        * glyphicons representing sort direction.
        * */
        var icon = elem.find(".glyphicon");
        icon.removeClass(sortOrderToGlyphicon[elem.attr("data-sort-order")]);

        elem.attr(
            "data-sort-order",
            sortSequence[
                (sortSequence.indexOf(elem.attr("data-sort-order")) + 1 + sortSequence.length)
                % sortSequence.length]);

        icon.addClass(sortOrderToGlyphicon[elem.attr("data-sort-order")])
    }

    $(".sort-field").click(function() {
        start = 0;
        cycleSort($(this));
        search();
    });
});