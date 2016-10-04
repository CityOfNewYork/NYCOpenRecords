$('#request-title').keyup(function () {
    var length = $(this).val().length;
    var length = 90 - length;
    $('#title-character-count').text(length + " characters remaining");
    if (length == 0) {
        document.getElementById("title-character-count").style.color = "red";
    } else {
        document.getElementById("title-character-count").style.color = "black";
    }
});
