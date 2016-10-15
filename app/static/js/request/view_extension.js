$(document).ready(function () {
    $(".add-extension .Div1").each(function (e) {
        if (e != 0)
            $(this).hide();
    });

    $("#next").click(function () {
        if ($(".add-extension .Div1:visible").next().length != 0)
            $(".add-extension .Div1:visible").next().show().prev().hide();
        else {
            $(".add-extension .Div1:visible").hide();
            $(".add-extension .Div1:first").show();
        }
        return false;
    });

    $("#previous").click(function () {
        if ($(".add-extension .Div1:visible").prev().length != 0)
            $(".add-extension .Div1:visible").prev().show().next().hide();
        else {
            $(".add-extension .Div1:visible").hide();
            $(".add-extension .Div1:last").show();
        }
        return false;
    });

    $("#dtpick").datepicker({
        dateFormat: "yy-mm-dd"
    });
});