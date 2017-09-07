"use strict";

$(window).resize(function () {
    var width = $(window).width();
    if (width >= 768) {
        $('#mobile-toggle').addClass('tabs-left');
    }
    else {
        $('#mobile-toggle').removeClass('tabs-left');
    }
}).resize();