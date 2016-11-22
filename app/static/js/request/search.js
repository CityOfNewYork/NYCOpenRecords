// success: function(resp){
//     // uncomment for full raw json response
//     // $('#results-raw').text(JSON.stringify(resp, null, 4));
//     var hits = typeof resp.hits != 'undefined' ? resp.hits.hits : resp;
//     if (hits.length > 0) {
//         for (var i = 0; i < hits.length; i++) {
//             var content = "";
//             if (typeof hits[i].highlight != 'undefined') {
//                 var keys = Object.keys(hits[i].highlight);
//                 for (var j = 0; j < keys.length; j++) {
//                     var key_private = null;
//                     if (keys[j] == "title") {
//                         key_private = hits[i]._source.title_private ?
//                                 "private" : "public";
//                     }
//                     else if (keys[j] == "agency_description") {
//                         key_private = hits[i]._source.agency_description_private ?
//                                 "private" : "public";
//                     }
//                     content += "<p><strong>" + keys[j] + "</strong>";
//
//                     if (key_private != null) {
//                         content += " <em>" + key_private + "</em>";
//                     }
//                     content += "<br>" + hits[i].highlight[keys[j]] + "</p>";
//                 }
//             }
//             var raw = JSON.stringify(hits[i], null, 4);
//             $('#results').append(
//                     "<li>" +
//                     "<a href='" + "/request/view/" + hits[i]._id + "'>" +
//                     hits[i]._id + "</a> : " + hits[i]._source.public_title +
//                     "<br>" + content +
//                     "<div class='show-raw'>{...}</div>" +
//                     "<div class='raw'>" + raw + "</div></li>");
//         }
//     }
// }



$(function() {
    function search(sortBy, start) {
        var results = $("#results");
        results.children().remove();  // clear rows

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
        var statusClosed = $("#closed").prop("checked");
        var statusDueSoon = $("#due-soon").prop("checked");
        var statusOverdue = $("#overdue").prop("checked");
        var pageSize = $("#size").val();

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
                agency: agency,
                open: statusOpen,
                closed: statusClosed,
                due_soon: statusDueSoon,
                overdue: statusOverdue,
                size: pageSize,
            },
            success: function(data) {
                if (data.total != 0) {
                    results.html(data.results);
                }
                else {
                    results.text("No results found.")
                }
            },
            error: function(e) {
                results.text("Hmmmm.... Looks like something's gone wrong.");
                console.log(e);
            }
        });
    }

    // TODO: cannot uncheck search filter if only 1 selected (both query and status)

    // disable other filters if searching by FOIL-ID
    $("#foil-id").click(function() {
        var query = $("#query");
        var ids = ["title", "description", "agency-desc", "requester-name"];
        var i;
        if ($(this).prop("checked")) {
            query.attr("placeholder", "0000-000-00000");
            for (i in ids) {
                $("#".concat(ids[i])).prop("disabled", true);
            }
        }
        else {
            query.attr("placeholder", "");
            for (i in ids) {
                $("#".concat(ids[i])).prop("disabled", false);
            }
        }
    });

    // TODO: order by filters, next/prev
    $("#search").click(search);
    $("#size").change(search);
});