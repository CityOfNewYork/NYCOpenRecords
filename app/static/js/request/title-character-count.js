$('#request-title').keyup(function() { 
        var length = $(this).val().length; 
        $('#title-character-count').text(length+" / 90 characters used"); });