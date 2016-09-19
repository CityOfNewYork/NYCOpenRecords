/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {
    // Apply parsley validation styles to the input forms for a new request.
    $('#request-title').attr('data-parsley-required', '');
    $('#request-title').attr('data-parsley-maxlength', 90);
    $('#request-agency').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-maxlength', 5000);
});
