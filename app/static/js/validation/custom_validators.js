/**
 * Created by atan on 9/27/16.
 */

"use strict";

window.Parsley.addValidator("maxFileSize", {
    validateString: function (_value, maxSize, parsleyInstance) {
        var files = parsleyInstance.$element[0].files;
        return files.length != 1 || files[0].size <= maxSize * 1000000;
    },
    requirementType: "integer",
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, the file cannot be larger than %s Mb.</strong> Please choose a smaller file."
    }
});

// Custom parsley validator to check if a date is valid. The function makes a ajax call to the backend
// and uses python's datetime library to validate the date.
window.Parsley.addValidator("validDate", {
    validateString: function (value) {
        if (value.length < 10) {
            return false;
        }
        var valid = false;
        $.ajax({
            url: "/request/api/v1.0/validate_date",
            type: "GET",
            async: false,
            data: {
                "date": value
            },
            success: function (data) {
                valid = data;
            },
            timeout: 5000
        });
        return valid;
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date is invalid.</strong> Please enter a valid date."
    }
});

// Custom parsley validator to check if the entered date is less than the current date.
window.Parsley.addValidator("dateLessThanToday", {
    validateString: function (value) {
        var enteredDate = new Date(value);
        var today = new Date();
        return enteredDate < today.setHours(0, 0, 0, 0);
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date is must be less than the current date.</strong> Please enter a valid date."
    }
});