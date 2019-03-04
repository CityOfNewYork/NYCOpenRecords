"use strict";

$(function() {

    var events = null;
    var index = 0;
    var indexIncrement = 5;
    var total = 0;
    var request_id = $.trim($("#request-id").text());
    var navButtons = $("#history-nav-buttons");
    var prevButton = navButtons.find(".prev");
    var nextButton = navButtons.find(".next");
    var requestHistory = $("#request-history");

    $.blockUI.defaults.css.border = "";
    $.blockUI.defaults.css.backgroundColor = "";
    $.blockUI.defaults.overlayCSS.backgroundColor = "gray";
    requestHistory.block({
        message: "<div class=\"col-sm-12 loading-container\"><div class=\"loading-spinner\">" +
        "<span class=\"sr-only\">Loading history...</span></div></div>"
    });

    $.ajax({
        url: "/request/api/v1.0/events",
        data: {
            start: 0,
            request_id: request_id,
            with_template: true
        },
        success: function (data) {
            events = data.events;
            total = data.total;
            if (events.length > indexIncrement) {  // if there are enough events to merit pagination
                navButtons.show();
                prevButton.attr("disabled", true);
            }
            $("#request-history-section").unblock();
            showHistory();
        },
        error: function(error) {
            console.log(error);
        }
    });

    function showHistory() {
        // clear history (events list)
        var history = $("#request-history");
        history.empty();

        if (events.length !== 0) {
            // advance index
            var indexIncremented = index + indexIncrement;
            var end = events.length < indexIncremented ? events.length : indexIncremented;
            for (var i = index; i < end; i++) {
                // add events html
                history.append(events[i].template);
            }
            flask_moment_render_all();
            $("#request-history-section").unblock();
        }
        else {
            // no events, history section remains empty
            history.text("");
        }
    }

    function loadMore() {
        $("#request-history").html("<div class='loading'></div>");
        $("#request-history-section").block({
            message: "<div class=\"col-sm-12 loading-container\"><div class=\"loading-spinner\">" +
            "<span class=\"sr-only\">Loading history...</span></div></div>"
        });
        $.ajax({
            url: "/request/api/v1.0/events",
            data: {
                start: events.length,
                request_id: request_id,
                with_template: true
            },
            success: function(data) {
                // append to events
                events = events.concat(data.events);
                if (index + indexIncrement >= total) {
                    nextButton.attr("disabled", true);
                }
            },
            error: function(error) {
                console.log(error);
            },
            complete: showHistory
        })
    }

    // replace currently displayed events with previous set
    prevButton.click(function () {
        nextButton.attr("disabled", false);
        if (index !== 0) {
            index -= indexIncrement;
            if (index == 0) {
                $(this).attr("disabled", true);
            }
            showHistory();
        }
    });

    // replace currently displayed events with next set
    nextButton.click(function () {
        prevButton.attr("disabled", false);
        index += indexIncrement;
        if (index === events.length) {
            loadMore();
        }
        else if (index + indexIncrement >= total) {
            nextButton.attr("disabled", true);
            showHistory();
        }
        else {
            showHistory();
        }
    })
});