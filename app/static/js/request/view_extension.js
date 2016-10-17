$(document).ready(function () {
    $(".add-extension .Div1").each(function (e) {
        if (e != 0)
            $(this).hide();
        else
            $("#previous").hide();
    });
    $("#add_extension").parsley().validate();

    $("#next").click(function () {
        if ($('#extension-select').parsley().isValid() == false){
            $('#extension-select').parsley().validate();
            preventDefault();
            // e.stopPropagation();
        }
        if ($('#dtpick').parsley().isValid() == false) {
            $('#dtpick').parsley().validate();
            preventDefault();
        }
            if ($(".add-extension .Div1:visible").next().length != 0) {
                $('#dtpick').parsley().reset();
                $(".add-extension .Div1:visible").next().show().prev().hide();
                $("#previous").show();
            }
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

    $("#extension-select").change(function () {
        selected = $(this).val();
        if (selected === "-1") {
            $("#custom_due_date").show();
        }
        else {
            $("#custom_due_date").hide();
        }
    });

    $("#dtpick").datepicker({
        dateFormat: "yy-mm-dd"
    });

    $('#extension-select').attr('data-parsley-required', '');
    $('#dtpick').attr('data-parsley-required','');
    $('#dtpick').attr('data-parsley-required-message', 'Extension date must be chosen');
    $('#extension-select').attr('data-parsley-required-message', 'Extension length must be selected');

});
