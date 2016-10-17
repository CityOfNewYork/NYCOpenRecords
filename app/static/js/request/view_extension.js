$(document).ready(function () {
    // Hides all other dives except for the first. Also hides previous button on the first div.
    $(".add-extension .Div1").each(function (e) {
        if (e != 0)
            $(this).hide();
        else
            $("#previous").hide();
    });

    // Handles click events on the next button
    $("#next").click(function (e) {
        if ($('#extension-select').parsley().isValid() == false){
            $('#extension-select').parsley().validate();
            e.preventDefault();
            e.stopImmediatePropagation();
            return false
        }
        if ($('#dtpick').parsley().isValid() == false) {
            $('#dtpick').parsley().validate();
            e.preventDefault();
            e.stopImmediatePropagation();
            return false
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

    // Handles click events on the previous button
    $("#previous").click(function () {
        if ($(".add-extension .Div1:visible").prev().length != 0)
            $(".add-extension .Div1:visible").prev().show().next().hide();
        else {
            $(".add-extension .Div1:visible").hide();
            $(".add-extension .Div1:last").show();
        }
        return false;
    });

    // Shows custom due date datepicker when Custom Due Date is selected
    $("#extension-select").change(function () {
        selected = $(this).val();
        if (selected === "-1") {
            $("#custom_due_date").show();
        }
        else {
            $("#custom_due_date").hide();
        }
    });

    // Datepicker for extension date of a request
    $("#dtpick").datepicker({
        dateFormat: "yy-mm-dd"
    });

    // Apply data-parsley-required attribute to specified fields
    $('#dtpick').attr('data-parsley-required','');
    $('#extension-select').attr('data-parsley-required', '');

    // Custom validation messages
    $('#dtpick').attr('data-parsley-required-message', 'Extension date must be chosen');
    $('#extension-select').attr('data-parsley-required-message', 'Extension length must be selected');
});
