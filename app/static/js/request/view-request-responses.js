// Initialize indexes
var request_responses_reload_index = 0;
var request_responses_index = 0;

// Hide load-more-responses div
$(".load-more-responses").hide();
var request_responses;
var request_responses_section;

$(document).ready(function () {
    $.ajax({
        type: "POST",
        url: '/request/api/v1.0/responses',
        data: {request_responses_reload_index: request_responses_reload_index},
        success: function (data) {
            request_responses = data.request_responses;
            request_responses_section = request_responses.slice(request_responses_index, request_responses_index + 10);
            console.log(request_responses);
            console.log(request_responses_section);
            var request_responses_html = '<table class="table"> <tbody>';
            for (var i = 0; i < 10; i++) {
                request_responses_html = request_responses_html + '<tr> <td>' + request_responses_section[i] + '<button style="float: right;" type="button" class="btn btn-secondary btn-sm">Edit</button> </td> </tr>';
            }
            console.log(request_responses_html);
            console.log(document.getElementById("request-responses-table"));
            document.getElementById("request-responses-table").innerHTML = request_responses_html;
        },
        error: function (error) {
            console.log(error);
        }
    });
});

function previous_responses() {
    if (request_responses_index != 0) {
        request_responses_index = request_responses_index - 10;
    }
    console.log(request_responses_index);
    request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 10)];
    if (request_responses_index == 90) {
        $(".load-more-responses").show();
    } else {
        $(".load-more-responses").hide();
    }
}

function next_responses() {
    if (request_responses_index != 90) {
        request_responses_index = request_responses_index + 10;
    }
    console.log(request_responses_index);
    request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 10)];
    if (request_responses_index == 90) {
        $(".load-more-responses").show();
    } else {
        $(".load-more-responses").hide();
    }
}

function load_more_responses() {
    request_responses_reload_index++;
    $.ajax({
        type: "POST",
        url: '/request/api/v1.0/responses',
        dataType: 'json',
        data: JSON.stringify(request_responses_reload_index),
        success: function (response) {
            var request_responses = response;
            var request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 10)];
            console.log(response)
        },
        error: function (error) {
            console.log(error);
        }
    });
    request_responses_index = 0;
}