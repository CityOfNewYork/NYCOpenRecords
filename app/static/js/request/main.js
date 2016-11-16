$(function() {
    $(".disable-enter-submit").keypress(function(e){
        if (e.keyCode == '13') {
           e.preventDefault();
        }
    });
});


function characterCounter (target, limit, currentLength) {
    /* Global character counter
     *
     * Parameters:
     * - target: string of target selector
     * - limit: integer of maximum character length
     * - currentLength: integer value of keyed in content
     *
     * Ex:
     * {
     *     target: "#note-content",
     *     charLength: 500,
     *     contentLength: $(this).val().length
     * }
     *
     * */
    var length = limit - currentLength;
    $(target).text(length + " characters remaining");
    if (length == 0) {
        $(target).css("color", "red");
    }
    else {
        $(target).css("color", "black");
    }
}


/* jquery datepicker */

// An array of holiday dates to be disabled
var holiday_dates = null;

function beforeShowDayNotHolidayOrWeekend(date) {
    /*
     * http://api.jqueryui.com/datepicker/#option-beforeShowDay
     *
     * WARNING:
     * --------
     * 'holiday_dates' must be set globally before calling this function.
     */
    var formattedDate = $.datepicker.formatDate('yy-mm-dd', date);
    var holiday_or_weekend = $.inArray(formattedDate, holiday_dates) !== -1 ||
            date.getDay() === 0 || date.getDay() === 6;
    // TODO: would be nice to display the name of the holiday (tooltip)
    return [!holiday_or_weekend];
}
