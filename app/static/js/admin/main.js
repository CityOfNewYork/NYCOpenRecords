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
        var isAgencyAdmin = $("input[name='is-admin']").is(":checked") ? true : null;
        var agencyEin = $("input[name='agency-ein']").val();
        $.ajax({
            url: "/user/" + id,
            type: "PATCH",
            data: {
                is_agency_active: true,
                is_agency_admin: isAgencyAdmin,
                agency_ein: agencyEin
            },
            success: function () {
                if (!alert("You will receive an email when the changes you requested have been completed.")) {
                    window.location.reload();
                }
            }
        });
    });

    // EDIT ACTIVE USER
    $("input[name^='user-status']").click(function () {
        var row = $(this).parents(".row");
        var id = row.find("input[name='user-id']").val();
        var isAgencyAdmin = row.find("input[name^='user-status']:checked").val();
        var agencyEin = $("input[name='agency-ein']").val();
        $.ajax({
            url: "/user/" + id,
            type: "PATCH",
            data: {
                is_agency_admin: isAgencyAdmin,
                agency_ein: agencyEin
            },
            success: function (data) {
                // Always returns a 200 response so that we can access the data
                var alertText = "";
                if (data["status"] === "Not Modified") {
                    alertText = "The user was not modified. No actions will be performed.";
                }
                else if (data["status"] === "success") {
                    alertText = "You will receive an email when the changes you requested have been completed.";
                }
                if (!alert(alertText)) {
                    window.location.reload();
                }
            }
        });
    });

    // REMOVE FROM ACTIVE USERS
    $("#remove").click(function () {
        var idsToRemove = $("input[name^='remove']:checked").parents(".row").find("input[name='user-id']");
        var agencyEin = $("input[name='agency-ein']").val();
        idsToRemove.each(function () {
            $.ajax({  // TODO: it would be better if this called a bulk-op endpoint 'users' *once*
                url: "/user/" + $(this).val(),
                type: "PATCH",
                data: {
                    is_agency_active: false,
                    is_agency_admin: false,
                    agency_ein: agencyEin
                },
                success: function () {
                    if (!alert("You will receive an email when the changes you requested have been completed.")) {
                        window.location.reload();
                    }
                }
            });
        });
    });
});