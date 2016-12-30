/**
 * Created by atan on 9/14/16.
 */
$(document).ready(function () {

    $("input[name='tz-name']").val(jstz.determine().name());

    // Prevent user from entering a non numeric value into phone and fax field
    $('#phone').keypress(function(key) {
        if (key.charCode != 0){
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });
    $('#fax').keypress(function(key) {
        if (key.charCode != 0){
            if (key.charCode < 48 || key.charCode > 57) {
                key.preventDefault();
            }
        }
    });

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

    // jQuery mask plugin to format fields
    $('#phone').mask("(999) 999-9999");
    $('#fax').mask("(999) 999-9999");
    $('#zipcode').mask("99999");

    // Datepicker for date request was received when creating a new request
    $(".dtpick").datepicker({
        dateFormat: "yy-mm-dd"
    }).keydown(false);

    // Loop through required fields and apply a data-parsley-required attribute to them
    var required_fields = ['request-title','request-description', 'request-agency', 'first-name','last-name','email',
        'phone','fax','address-line-1', 'method-received','request-date', 'city','zipcode'];
    for (i = 0 ; i < required_fields.length ; i++){
        $('#' + required_fields[i]).attr('data-parsley-required','');
    }

    // Apply parsley validation styles to the input forms for a new request.
    $('#request-title').attr('data-parsley-maxlength', 90);
    $('#request-description').attr('data-parsley-maxlength', 5000);
    $("#email").attr("data-parsley-maxlength", 254);
    $('#phone').attr('data-parsley-length','[14,14]');
    $('#fax').attr('data-parsley-length','[14,14]');
    $('#zipcode').attr('data-parsley-length', '[5,5]');

    // Custom Validation Messages
    $('#fax').attr('data-parsley-length-message', 'The fax number must be 10 digits.');
    $('#phone').attr('data-parsley-length-message', 'The phone number must be 10 digits.');
    $('#zipcode').attr('data-parsley-length-message', 'The Zipcode must be 5 digits.');

    // Disable default error messages for email,phone,fax,address so custom one can be used instead.
    $('#phone').attr('data-parsley-required-message', '');
    $('#fax').attr('data-parsley-required-message', '');
    $('#address-line-1').attr('data-parsley-required-message', '');
    $('#city').attr('data-parsley-required-message','');
    $('#email').attr('data-parsley-required-message', '');
    $('#zipcode').attr('data-parsley-required-message','');

    // Limit the size of the file upload to 20 Mb. Second parameter is number of Mb's.
    $('#request-file').attr('data-parsley-max-file-size',"20");

    // Specify container for file input parsley error message
    $('#request-file').attr("data-parsley-errors-container", ".file-error");

    // Set name of the file to the text of filename div if file exists
    $("#request-file").change(function () {
        var file = this.files[0];
        var isChrome = window.chrome;

        if(file) {
            $("#filename").text((this.files[0].name));
        }
        // Cancel is clicked on upload window
        else {
            // If browser is chrome, reset filename text
            if(isChrome) {
                $("#filename").text("");
            }
        }
    });

    // Clear the file from input and the name from filename div
    $("#clear-file").click(function () {
        if ($(".file-error").is(":visible")) {
            $(".file-error").hide();
        }
        $("#request-file").val("");
        $("#filename").text("");
    });

    // Contact information validation
    $('#email').attr('data-parsley-type', 'email');
    // Called when validation is used and checks that at least one form of contact was filled out
    $('#request-form').parsley().on('form:validate', function (formInstance) {
        // Re-apply validators to fields in the event that they were removed from previous validation requests.
        for (i = 0 ; i < required_fields.length ; i++){
           $('#' + required_fields[i]).attr('data-parsley-required','');
        }
        // If address is filled out then make sure the city, state, and zipcode are filled.
        if ($('#address-line-1').parsley().isValid()){
                $('#city').attr('data-parsley-required','');
                $('#state').attr('data-parsley-required','');
                $('#zipcode').attr('data-parsley-required','');
            }
        // Checks that at least one of the contact information fields is filled in addition to the rest of the form
        if ($('#email').parsley().isValid() ||
            $('#phone').parsley().isValid() ||
            $('#fax').parsley().isValid() ||
            ($('#address-line-1').parsley().isValid() &&
            $('#state').parsley().isValid() &&
            $('#zipcode').parsley().isValid() &&
            $('#city').parsley().isValid())
            &&
            ($('#request-agency').parsley().isValid() &&
            $('#request-title').parsley().isValid() &&
            $('#request-description').parsley().isValid() &&
            $('#first-name').parsley().isValid() &&
            $('#last-name').parsley().isValid())
        ) {
            // If at least one of the fields are validated then remove required from the rest of the contact fields that aren't being filled out
                $('#city').removeAttr('data-parsley-required');
                $('#state').removeAttr('data-parsley-required');
                $('#zipcode').removeAttr('data-parsley-required');
                $('#phone').removeAttr('data-parsley-required');
                $('#fax').removeAttr('data-parsley-required');
                $('#address-line-1').removeAttr('data-parsley-required');
                $('#email').removeAttr('data-parsley-required');
        }
        else {
            // If none of the fields are valid then produce an error message and apply required fields.
            $('.contact-form-error-message').html("*At least one of the following must be filled out: Email, Phone, Fax, and/or Address (with City, State, and Zipcode)");
            $('#fax').attr('data-parsley-required', '');
            $('#phone').attr('data-parsley-required', '');
            $('#address-line-1').attr('data-parsley-required', '');
            $('#email').attr('data-parsley-required', '');
        }

        if ($("#request-file").parsley().isValid() === false) {
            $(".file-error").show();
        }
        else {
            $(".file-error").hide();
        }

        // Scroll to input label if parsley validation fails
        if ($("#request-title").parsley().isValid() === false) {
            $(window).scrollTop($(".title-label").offset().top);
        }
        else if ($("#request-description").parsley().isValid() === false ) {
            $("#request-description").attr('data-parsley-no-focus', '');
            $(window).scrollTop($(".description-label").offset().top);
        }
        else if ($("#request-file").parsley().isValid() === false) {
            $(".file-error").show();
            $(window).scrollTop($("#upload-control").offset().top);
        }
        else if ($("#method-received").parsley().isValid() === false ) {
            $(window).scrollTop($(".format-label").offset().top);
        }
        else if ($("#first-name").parsley().isValid() === false ) {
            $(window).scrollTop($(".first-name-label").offset().top);
        }
        else if ($("#last-name").parsley().isValid() === false ) {
            $(window).scrollTop($(".last-name-label").offset().top);
        }
        else if ($("#email").parsley().isValid() === false ) {
            $(window).scrollTop($(".email-label").offset().top);
        }
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
        $('#submit').hide();
        $('#processing-submission').show()
    });

    // Character count for creating a new request
    $('#request-title').keyup(function () {
        characterCounter("#title-character-count", 90, $(this).val().length)
    });

    $('#request-description').keyup(function () {
        characterCounter("#description-character-count", 5000, $(this).val().length)
    });

});
