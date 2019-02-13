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

window.Parsley.addValidator("date", {
    validateString: function (value) {
        if (value.length < 10) {
            return false;
        }

        var enteredDate = new Date(value);
        var today = new Date();

        return !(isNaN(enteredDate.getMonth()) || isNaN(enteredDate.getDate()) || enteredDate > today.setHours(0, 0, 0, 0));
    },
    messages: {
        en: "<span class=\"glyphicon glyphicon-exclamation-sign\"></span>&nbsp;" +
        "<strong>Error, this date is invalid.</strong> Please enter a valid date."
    }
});