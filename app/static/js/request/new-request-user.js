/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {

    $('[data-toggle="popover"]').popover();

    // javascript to add tooltip popovers when selecting the title and description
    $('#request-title').attr({
            'data-placement': "top",
            'data-trigger': "hover focus",
            'data-toggle': "popover",
            'data-content': "Public Advocate Emails from 2015",
            title: "Example Title"
    });
    $('#request-title').popover();
    // $('#request-title').click(function(){
    //     $('#request-title').popover('show');
    // });
    
    $('#request-description').attr({
            'data-placement': "top",
            'data-trigger': "hover focus",
            'data-toggle': "popover",
            'data-content': "Topic: Public Advocate Emails from 2015. Emails that mention bike lanes or bicycle lanes from the Public Advocate's Office between July 27, 2015 and September 10, 2015.",
            title: "Example Request"
    });
    $('#request-description').click(function(){
        $('#request-description').popover('show');
    });
    $('#request-description').popover();
    // $('#request-description').click(function(){
    //     $('#request-description').popover('show');
    // });

    // Apply parsley validation styles to the input forms for a new request.
    $('#request-title').attr('data-parsley-required', '');
    $('#request-title').attr('data-parsley-maxlength', 90);
    $('#request-agency').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-required', '');
    $('#request-description').attr('data-parsley-maxlength', 5000);

    // Limit the size of the file upload to 20 Mb. Second parameter is number of Mb's.
    $('#request-file').attr('data-parsley-max-file-size',"20");

    $('#request-form').parsley().subscribe('parsley:form:validate', function () {
        // Do stuff when parsley validates
        // TODO: this or combine (see the other new-request-* js files)
    });

    // Clear error messages for form.request_file on submit ...
    $('#submit').click(function() {
        $('.upload-error').remove();
    });
    // ... or on input change for request_file
    $('#request-file').change(function() {
        $('.upload-error').remove();
    });

    // Disable submit button on form submission
    $('#request-form').submit(function() {
        $('#submit').prop('disabled', true);  // TODO: display a spinner
    });
});
