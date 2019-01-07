"use strict";


function generateFaqClickHandler(id) {
    /*
     * This function creates faq link click handlers for when you have multiple events inside a loop
     */
    return function (e) {
        e.preventDefault();
        $(window).scrollTop($("#faq-answer-" + id).offset().top - 50);
        $("#faq-answer-" + id).focus();
    };
}

$(document).ready(function () {
    // Focus on FAQ header when Back to Top is clicked
    $(".back-to-top").click(function () {
        $("#faq-header").focus();
    });

    // Create handlers to focus on the FAQ answer paragraph when the link is clicked
    $(".faq-link").each(function (index) {
        $("#" + this.id).click(generateFaqClickHandler(index + 1));
    });
});
