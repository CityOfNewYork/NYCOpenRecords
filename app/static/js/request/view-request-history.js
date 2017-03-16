$(function() {

    var events = null;
    var index = 0;
    var index_increment = 5;
    var request_id = $.trim($("#request-id").text());
    var navButtons = $("#history-nav-buttons");
    var prevButton = navButtons.find(".prev");
    var nextButton = navButtons.find(".next");

    $.ajax({
        url: "/request/api/v1.0/events",
        data: {
            start: 0,
            request_id: request_id,
            with_template: true
        },
        success: function (data) {
            events = data.events;
            if (events.length > index_increment) {  // if there are enough events to merit pagination
                navButtons.show();
                prevButton.attr("disabled", true);
            }
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
            var index_incremented = index + index_increment;
            var end = events.length < index_incremented ? events.length : index_incremented;
            for (var i = index; i < end; i++) {
                // add events html
                history.append(events[i].template);
            }
            flask_moment_render_all();
        }
        else {
            // no events, history section remains empty
            history.text("");
        }
    }

    function loadMore() {
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
                if (events.length - index_increment == index) {
                    nextButton.attr("disabled", true);
                }
            },
            error: function(error) {
                console.log(error);
            }
        })
    }

    // replace currently displayed events with previous set
    prevButton.click(function () {
        nextButton.attr("disabled", false);
        if (index !== 0) {
            index -= index_increment;
            if (index == 0) {
                $(this).attr("disabled", true);
            }
            showHistory();
        }
    });

    // replace currently displayed events with next set
    nextButton.click(function () {
        prevButton.attr("disabled", false);
        index += index_increment;
        if (index == events.length - index_increment) {
            loadMore();
        }
        if (events.length < index + index_increment) {
            nextButton.attr("disabled", true);
        }
        if (events.length < index) {
            index -= index_increment;
        }
        showHistory();
    })
});