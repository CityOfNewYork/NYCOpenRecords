$('#request-description').keyup(function () {
    var length = $(this).val().length;
    var length = 5000 - length;
    $('#description-character-count').text(length + " characters remaining");
    if (length == 0) {
        document.getElementById("description-character-count").style.color = "red";
    } else {
        document.getElementById("description-character-count").style.color = "black";
    }
});
