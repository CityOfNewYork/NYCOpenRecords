$(function() {
    var start = 0;
    var end = 0;
    var total = 0;

    function search() {

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
                agency: agency,
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
                    $("#page-info").text(
                        (start + 1) + " - " +
                        (start + data.count) +
                        " of " + data.total
                    );
                    total = data.total;
                    count = data.count;
                    end = start + data.count;
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
    $("#next").click(function() {
        if (end < total) {
            start += parseInt($("#size").val());
            search();
        }
    });
    $("#prev").click(function() {
        if (start > 0) {
            start -= parseInt($("#size").val());
            search();
        }
    });

    // SORTING

    $(".sort-field").click(function() {
        start = 0;
        toggleSort($(this));
        search();
    });

    var sortOrderToGlyphicon = {
        desc: "glyphicon-triangle-bottom",
        asc: "glyphicon-triangle-top",
        none: "",
    };

    var sortSequence = ["none", "desc", "asc"];

    function toggleSort(elem) {
        var icon = elem.find(".glyphicon");
        icon.removeClass(sortOrderToGlyphicon[elem.attr("data-sort-order")]);

        elem.attr(
            "data-sort-order",
            sortSequence[
                (sortSequence.indexOf(elem.attr("data-sort-order")) + 1 + sortSequence.length)
                % sortSequence.length]);

        icon.addClass(sortOrderToGlyphicon[elem.attr("data-sort-order")])
    }
});