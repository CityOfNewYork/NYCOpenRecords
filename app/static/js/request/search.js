$(function() {

    // set time zone name
    $("input[name='tz_name']").val(jstz.determine().name());

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

    function valiDates(fromDateElem, toDateElem) {
        /*
        * Check that 'fromDateElem' is less than 'toDateElem'
        * and that both dates are not holidays or weekends.
        * */
        valiDate(fromDateElem, toDateElem, true);
        valiDate(toDateElem, fromDateElem, false);
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

    // keypress 'Enter' = click search button
    $("#search-section").keyup(function(e){
        if(e.keyCode === 13) {
            $("#search").click();
        }
    });
    // but don't submit form (generate csv)
    $("#search-form").on("keyup, keypress", function(e){
        var keyCode = e.keyCode || e.which;
        if (keyCode === 13) {
            e.preventDefault();
            return false;
        }
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

    var next = $("#next");
    var prev = $("#prev");
    var generateDocBtn = $("#generate-document");

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
                    results.html(data.results);
                    flask_moment_render_all();
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
                    generateDocBtn.attr("disabled", false);
                }
                else {
                    results.html("<li class='list-group-item text-center'>" +
                        "No results found.</li>");
                    pageInfo.text("");
                    next.hide();
                    prev.hide();
                    generateDocBtn.attr("disabled", true);
                }
            },
            error: function(e) {
                results.html("<li class='list-group-item text-center'>" +
                    "Hmmmm.... Looks like something's gone wrong.</li>");
                pageInfo.text("");
                next.hide();
                prev.hide();
                generateDocBtn.attr("disabled", true);
            }
        });
    }

    // search on load
    search();

    // disable other filters if searching by FOIL-ID
    $("input[name='foil_id']").click(function() {
        var query = $("#query");
        var names = ["title", "description", "agency_description", "requester_name"];
        var i;
        if ($(this).prop("checked")) {
            query.attr("placeholder", "0000-000-00000");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", true);
            }
        }
        else {
            query.attr("placeholder", "");
            for (i = 0; i < names.length; i++) {
                $("input[name='" + names[i] + "']").prop("disabled", false);
            }
        }
    });

    function setStart(val) {
        start = val;
        $("input[name='start']").val(val);
    }

    generateDocBtn.click(function() {
        search();
    });
    $(".status").click(function() {
        setStart(0);
        search();
    });
    $("#search").click(function() {
        setStart(0);
        search();
    });
    $("#size").change(function() {
        setStart(0);
        search();
    });
    $("#agency_ein").change(function() {
        setStart(0);
        search();
    });
    next.click(function() {
        if (end < total) {
            setStart(start + parseInt($("#size").val()));
            search();
        }
    });
    prev.click(function() {
        if (start > 0) {
            setStart(start - parseInt($("#size").val()));
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

        icon.addClass(sortOrderToGlyphicon[elem.attr("data-sort-order")]);
    }

    $(".sort-field").click(function() {
        setStart(0);
        cycleSort($(this));
        // fill hidden inputs
        $("input[name='" + $(this).attr("id") + "']").val($(this).attr("data-sort-order"));
        search();
    });
});