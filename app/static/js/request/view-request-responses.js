// Initialize indexes
var request_responses_reload_index = 0;
var request_responses_index = 0;

// Hide load-more-responses div
$(".load-more-responses").hide();
var request_responses = [];
var request_responses_section = [request_responses.slice(request_history_index, request_history_index + 6)];

// $(document).ready(function () {
//     $.ajax({
//         type: "POST",
//         url: '/request/_get_request_responses',
//         dataType: 'json',
//         data: JSON.stringify(request_responses_reload_index),
//         success: function (response) {
//             var request_responses = response;
//             var request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 11)];
//             console.log(response)
//         },
//         error: function (error) {
//             console.log(error);
//         }
//     });
// });

function previous_responses() {
    if (request_responses_index != 0) {
        request_responses_index = request_responses_index - 10;
    }
    console.log(request_responses_index);
    request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 11)];
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
    request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 11)];
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
        url: '/_get_request_responses',
        dataType: 'json',
        data: JSON.stringify(request_responses_reload_index),
        success: function (response) {
            var request_responses = response;
            var request_responses_section = [request_responses.slice(request_responses_index, request_responses_index + 11)];
            console.log(response)
        },
        error: function (error) {
            console.log(error);
        }
    });
    request_responses_index = 0;
}