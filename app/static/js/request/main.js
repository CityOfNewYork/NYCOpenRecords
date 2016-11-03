$(function() {
    $(".disable-enter-submit").keypress(function(e){
        if (e.keyCode == '13') {
           e.preventDefault();
        }
    });
});
