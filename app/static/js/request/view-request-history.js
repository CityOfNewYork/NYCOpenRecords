// Initialize indexes
var request_history_reload_index = 0;
var request_history_index = 0;

// Hide load-more-history div
$(".load-more-history").hide();
var request_history;

$(document).ready(function () {
    $.ajax({
        type: "POST",
        url: '/request/api/v1.0/history',
        data: {request_history_reload_index: request_history_reload_index},
        success: function (data) {
            request_history = data.request_history;
            var request_history_html = '<table class="table"> <tbody>';
            for (var i = request_history_index; i < request_history_index + 5; i++) {
                request_history_html = request_history_html + '<tr> <td>' + request_history[i] + '</td> </tr>';
            }
            document.getElementById("request-history-table").innerHTML = request_history_html;
        },
        error: function (error) {
            console.log(error);
        }
    });
});

function previous_history() {
    if (request_history_index != 0) {
        request_history_index = request_history_index - 5;
        var request_history_html = '<table class="table"> <tbody>';
        for (var i = request_history_index; i < request_history_index + 5; i++) {
            request_history_html = request_history_html + '<tr> <td>' + request_history[i] + '</td> </tr>';
        }
        document.getElementById("request-history-table").innerHTML = request_history_html;
    }
    if (request_history_index == request_history.length - 5) {
        $(".load-more-history").show();
    } else {
        $(".load-more-history").hide();
    }
}

function next_history() {
    if (request_history_index != request_history.length - 5) {
        request_history_index = request_history_index + 5;
        var request_history_html = '<table class="table"> <tbody>';
        for (var i = request_history_index; i < request_history_index + 5; i++) {
            request_history_html = request_history_html + '<tr> <td>' + request_history[i] + '</td> </tr>';
        }
        document.getElementById("request-history-table").innerHTML = request_history_html;
    }
    if (request_history_index == request_history.length - 5) {
        $(".load-more-history").show();
    } else {
        $(".load-more-history").hide();
    }
}

function load_more_history() {
    request_history_reload_index++;
    $.ajax({
        type: "POST",
        url: '/request/api/v1.0/history',
        data: {request_history_reload_index: request_history_reload_index},
        success: function (data) {
            request_history = data.request_history;
            var request_history_html = '<table class="table"> <tbody>';
            for (var i = request_history_index; i < request_history_index + 5; i++) {
                request_history_html = request_history_html + '<tr> <td>' + request_history[i] + '</td> </tr>';
            }
            document.getElementById("request-history-table").innerHTML = request_history_html;
        },
        error: function (error) {
            console.log(error);
        }
    });
    $(".load-more-history").hide();
}