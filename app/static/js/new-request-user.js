/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {
    // Apply parsley validation styles to the input forms for a new request.
    document.getElementById('request-title').setAttribute('data-parsley-required', '');
    document.getElementById('request-title').setAttribute('data-parsley-maxlength', 90);
    document.getElementById('request-agency').setAttribute('data-parsley-required', '');
    document.getElementById('request-description').setAttribute('data-parsley-required', '');
    document.getElementById('request-description').setAttribute('data-parsley-maxlength', 5000);
});
