"use strict";

$(function () {
    // SWITCH AGENCY
    $("#agencies").change(function () {
        var agencyEin = $(this).val();
        window.location = window.location.origin + "/admin/" + agencyEin;
    });
    // ACTIVATE AGENCY
    $("#activate").click(function () {
        var agencyEin = $("#agencies").val();
        $.ajax({
            url: "/agency/" + agencyEin,
            type: "PATCH",
            data: {
                is_active: true
            },
            success: function () {
                window.location = window.location.origin + "/admin/" + agencyEin;
            }
        });
    });
    // DEACTIVATE AGENCY
    $("#deactivate").click(function () {
        var agencyEin = $("#agencies").val();
        $.ajax({
            url: "/agency/" + agencyEin,
            type: "PATCH",
            data: {
                is_active: false
            },
            success: function () {
                window.location = window.location.origin + "/admin/" + agencyEin;
            }
        });
    });
    // SET SUPER USER
    $("input[name^='user-super']").click(function () {
        var row = $(this).parents(".row");
        var id = row.find("input[name='user-id']").val();
        var isSuperUser = $(this).is(":checked");
        $.ajax({
            url: "/user/" + id,
            type: "PATCH",
            data: {
                is_super: isSuperUser
            }
        });
    });
    // ADD ACTIVE USER
    $("#add-button").click(function () {
        var id = $("#users").val();
        var isAgencyAdmin = $("input[name='is-admin']").is(":checked");
        var agencyEin = $("input[name='agency-ein']").val();
        $("#add-agency-users").block({
            message: "<img src='/static/img/loading.gif' height='40' width='40'>"
        });
        $.ajax({
            url: "/user/" + id,
            type: "PATCH",
            data: {
                is_agency_active: true,
                is_agency_admin: isAgencyAdmin,
                agency_ein: agencyEin
            },
            success: function () {
                $("#add-agency-users").unblock();
                location.reload();
            }
        });
    });
    // EDIT ACTIVE USER
    $("input[name^='user-status']").click(function () {
        var row = $(this).parents(".row");
        var id = row.find("input[name='user-id']").val();
        var splitId = id.split("|");
        var isAgencyAdmin = row.find("input[name^='user-status']:checked").val();
        var agencyEin = $("input[name='agency-ein']").val();
        $("#" + splitId[0]).block({
            message: "<img src='/static/img/loading.gif' height='40' width='40'>"
        });
        $.ajax({
            url: "/user/" + id,
            type: "PATCH",
            data: {
                is_agency_admin: isAgencyAdmin,
                agency_ein: agencyEin
            },
            success: function () {
                $("#" + splitId[0]).unblock();
            }
        });
    });
    // REMOVE FROM ACTIVE USERS
    $("#remove").click(function () {
        var idsToRemove = $("input[name^='remove']:checked").parents(".row").find("input[name='user-id']");
        var agencyEin = $("input[name='agency-ein']").val();
        idsToRemove.each(function () {
            var splitId = $(this).val().split("|");
            $("#" + splitId[0]).block({
                message: "<img src='/static/img/loading.gif' height='40' width='40'>"
            });
            $.ajax({  // TODO: it would be better if this called a bulk-op endpoint 'users' *once*
                url: "/user/" + $(this).val(),
                type: "PATCH",
                data: {
                    is_agency_active: false,
                    is_agency_admin: false,
                    agency_ein: agencyEin
                },
                success: function () {
                    $("#" + splitId[0]).unblock();
                    location.reload();
                }
            });
        });
    });
});
