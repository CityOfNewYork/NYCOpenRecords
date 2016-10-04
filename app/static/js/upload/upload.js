/**
 * Created by atan on 10/1/16.
 */

$(document).ready(function () {
    tinymce.init({
        selector: 'textarea',
        height: 500,
        plugins: [
            'advlist autolink lists link image charmap print preview anchor',
            'searchreplace visualblocks code fullscreen',
            'insertdatetime table contextmenu paste code'
        ],
        toolbar: 'insertfile undo redo | styleselect | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent',
    });

    //Call ajax to populate email field with content after textarea is finished loading.
    window.onload =function(){
        $.ajax({
            url: "/upload/email",
            type: 'POST',
            processData: false,
            contentType: false,
            success: function (data) {
                //Data should be html template page.
                tinyMCE.get('email_content').setContent(data);
            },
            error: function (data) {
                alert('fail.');
            }
        });
        $('.prev-slider,.next-slider').click(function () {
            $("#email_summary").html(tinyMCE.get('email_content').getContent());
        });
    };







});