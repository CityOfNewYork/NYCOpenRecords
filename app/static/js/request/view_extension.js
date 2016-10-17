$(document).ready(function () {
    // Hides all other divs except for the first. Also hides previous button on the first div.
    $(".add-extension .Div1").each(function (e) {
        if (e != 0)
            $(this).hide();
        else
            $("#previous").hide();
    });

    // Handles click events on the next button
    $("#next_btn1").click(function (e) {
        if ($("#dtpick").is(':visible')) {
            $("#dtpick").parsley().validate();
            if (!$('#dtpick').parsley().isValid()) {
                e.preventDefault();
                return false;
            }
        }
        $('#extension-select').parsley().validate();
        if ($('#extension-select').parsley().isValid() || $('#dtpick').parsley().isValid()) {
            document.getElementById("first").style.display = "none";
            document.getElementById("second").style.display = "block";
        }
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

// Apply parsley validation styles to input fields of adding an extension
$('#dtpick').attr('data-parsley-required', '');
$('#extension-select').attr('data-parsley-required', '');

// Apply custom validation messages
$('#dtpick').attr('data-parsley-required-message', 'Extension date must be chosen');
$('#extension-select').attr('data-parsley-required-message', 'Extension length must be selected');
});