/* Global character counter
 *
 * Parameters:
 * - target: string of target selector
 * - charLength: integer of maximum character length
 * - contentLength: integer value of keyed in content
 *
 * Ex:
 * {
 *     target: "#note-content",
 *     charLength: 500,
 *     contentLength: $(this).val().length
 * }
 *
 * */
function characterCounter (target, charLength, contentLength) {
    var length = charLength - contentLength;
    $(target).text(length + " characters remaining");
    if (length == 0) {
        $(target).css("color", "red");
    }
    else {
        $(target).css("color", "black");
    }
}

// Character count for creating a new request
$('#request-title').keyup(function () {
    characterCounter("#title-character-count", 90, $(this).val().length)
});

$('#request-description').keyup(function () {
    characterCounter("#description-character-count", 5000, $(this).val().length)
});