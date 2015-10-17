$(function() {
    $('#step1').fadeIn('fast');
   
    var validContact = false;
    var validAddress = false;

    $('#submitRequest').validate({
        rules: {
            request_agency: {
                required: true
            },
            request_summary: {
                required: true
            },
            request_text: {
                required: true
            },
            request_first_name: {
                required: true
            },
            request_last_name: {
                required: true
            }
        },
        highlight: function (element) {
            $(element).closest('.control-group').removeClass('success').addClass('error');
        }
    });

    $('#button1').click(function() {

      if($('#submitRequest').valid()) {
          // scroll to the top of the form
          $('html, body').animate({
            scrollTop: $("#submitRequest").offset().top
          }, 500);

          // fade out step1, fade in step2
          $('#step1').fadeOut('fast', function() {});
          $('#step2').fadeIn('slow', function() {});
          $('#s1').removeClass('active');
          $('#s2').addClass('active');
      }

    });

    $('#button2').click(function(e) {

        if($('#request_address_street_one').val() && $('#request_address_city').val() && $('#request_address_zip').val()) {
            validAddress = true;
        }

        if($('#request_email').val() || $('#request_email').val() || $('#request_email').val() || validAddress) {
            validContact = true;
        }

        if($('#submitRequest').valid() && !validContact) {
            e.preventDefault();
            $('#missing_contact_information').show();
            $('#request_email').focus();
        }
    });

    $('#back').click(function() {
        // scroll to the top of the form
        $('html, body').animate({
            scrollTop: $("#submitRequest").offset().top
        }, 500);

        // fade out step1, fade in step2
        $('#step2').fadeOut('fast', function() {});
        $('#step1').fadeIn('slow', function() {});
    });
    $('#s1 a').click(function() {
        // when step one is clicked, go to step 1

        if (Modernizr.touch) {
            $('html, body').animate({
                scrollTop: $("#submitRequest").offset().top
            }, 500);
        } else {
            // don't scroll to the top
        }


        $('#step2').fadeOut('fast', function() {});
        $("#s2").removeClass("active");
        $("#s1").addClass("active");
        $('#step1').fadeIn('slow', function() {});
    });

    $('#s2 a').click(function() {
        // when step two is clicked, go to step 1

        // validation

        if (!$('#agency').val() || !$('#request_summary').val()) {
            alert("All indicated information is required. Please complete all fields");
            exit();
        }

        if (Modernizr.touch) {
            $('html, body').animate({
                scrollTop: $("#submitRequest").offset().top
            }, 500);
        } else {
            // don't scroll to the top
        }

        $('#step1').fadeOut('fast', function() {});
        $("#s1").removeClass("active");
        $("#s2").addClass("active");
        $('#step2').fadeIn('slow', function() {});
    });

    function maxLength(el) {    
    if (!('maxLength' in el)) {
        var max = el.attributes.maxLength.value;
        el.onkeypress = function () {
            if (this.value.length >= max) return false;
        };
    }
}

maxLength(document.getElementById("request_summary"));

});
