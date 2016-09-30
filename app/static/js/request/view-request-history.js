// Initialize indexes
var request_history_reload_index = 0;
var request_history_index = 0;

// Hide load-more-history div
$(".load-more-history").hide();
var request_history = [];
var request_history_section = [request_history.slice(request_history_index, request_history_index + 6)];

$(document).ready(function () {
    $.ajax({
        type: "POST",
        url: '/request/api/v1.0/history',
        data: {request_history_reload_index: request_history_reload_index},
        success: function (data) {
            // var request_history = data;
            // var request_history_section = [request_history.slice(request_history_index, request_history_index + 6)];
            console.log(data.request_history);
        },
        error: function (error) {
            console.log(error);
        }
    });
});

function previous_history() {
    if (request_history_index != 0) {
        request_history_index = request_history_index - 5;
    }
    console.log(request_history_index);
    request_history_section = [request_history.slice(request_history_index, request_history_index + 6)];
    if (request_history_index == 45) {
        $(".load-more-history").show();
    } else {
        $(".load-more-history").hide();
    }
}

function next_history() {
    if (request_history_index != 45) {
        request_history_index = request_history_index + 5;
    }
    console.log(request_history_index);
    request_history_section = [request_history.slice(request_history_index, request_history_index + 6)];
    if (request_history_index == 45) {
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
        dataType: 'json',
        data: JSON.stringify(request_history_reload_index),
        success: function (response) {
            var request_history = response;
            var request_history_section = [request_history.slice(request_history_index, request_history_index + 6)];
            console.log(response)
        },
        error: function (error) {
            console.log(error);
        }
    });
    request_history_index = 0;
}