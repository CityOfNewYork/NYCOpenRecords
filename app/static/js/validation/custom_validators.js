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

// Custom parsley validator to check if a date is valid using the Moment.js library
window.Parsley.addValidator("validDate", {
    validateString: function (value) {
        if (value.length < 10) {
            return false;
        }
        var enteredDate = moment(value, "MM/DD/YYYY", true);
        return enteredDate._isValid;
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date is invalid.</strong> Please enter a valid date."
    }
});

// Custom parsley validator to check the entered date and display an error if it is in the past.
window.Parsley.addValidator("pastDateInvalid", {
    validateString: function (value) {
        var enteredDate = new Date(value).setHours(0, 0, 0, 0);
        var currentDate = new Date().setHours(0, 0, 0, 0);
        return enteredDate >= currentDate;
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date cannot be a past date.</strong> Please enter a valid date."
    }
});

// Custom parsley validator to check the entered date and display an error if it is equal to the current date.
window.Parsley.addValidator("currentDateInvalid", {
    validateString: function (value) {
        var enteredDate = new Date(value).setHours(0, 0, 0, 0);
        var currentDate = new Date().setHours(0, 0, 0, 0);
        return enteredDate !== currentDate;
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date cannot be the current date.</strong> Please enter a valid date."
    }
});

// Custom parsley validator to check the entered date and display an error if it is in the future.
window.Parsley.addValidator("futureDateInvalid", {
    validateString: function (value) {
        var enteredDate = new Date(value).setHours(0, 0, 0, 0);
        var currentDate = new Date().setHours(0, 0, 0, 0);
        return enteredDate <= currentDate;
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date cannot be in the future.</strong> Please enter a valid date."
    }
});