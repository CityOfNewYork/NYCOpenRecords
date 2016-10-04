$('#request-description').keyup(function() { 
        var length = $(this).val().length; 
        $('#description-character-count').text(length+" / characters 5000 used"); });