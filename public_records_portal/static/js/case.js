(function () {
    // if ($('#record').record('active') > 0){
    //     alert("Actively uploading"):
    // }

    // Changes the height of the modal to a protion of the screen's size
    $('.modal-content').css('height', $(window).height() * 0.8);

    $('#load-more-qa').on('click', function () {
        $.getJSON('/api/request/2', function (data) {
            var html = '';
            var qas = data.qas;
            for (var i = 0; i < qas.length; i++) {
                var qa = qas[i];
                html += qa_to_html(qa);
            }
            $('#load-more-qa').before(html);
        });
    });

    function qa_to_html(qa) {
        return '<h3>' + qa.date_created + '</h3>';
    }

    // hide/show responses
    var $responses = $('.response');
    hideExcept([0], $responses);

    // hides elements, can take a whitelist of indexes
    // ex: to hide all but first ->
    //    hideExcept([0], $elem);
    function hideExcept(whitelist, elem) {
        $.each(elem,
            function (i, el) {
                if ($.inArray(i, whitelist) == -1) {
                    $(el).hide();
                }
            });
    }

    $('.case-show-all').on('click', function () {
        var $this = $(this);
        if ($(this).hasClass('show')) {
            $this.toggleClass('show');
            $responses.show(200);
            $this.html('<i class="icon-chevron-up"></i> See less <i class="icon-chevron-up"></i>')
        } else {
            $this.toggleClass('show');
            hideExcept([0], $responses);
            $this.html('<i class="icon-chevron-down"></i> See all <i class="icon-chevron-down"></i>')
        }
    });
    $('#acknowledgeRequestForm').on('click', function () {
        if ($('#acknowledgeRequestForm').css('display') != 'none') {
            $('#acknowledgeRequestForm').hide();
        }
    });

    $("#days_after").change(function () {
        selected = $(this).val();
        if (selected === "0") {
            $("#custom_due_date").show();
        }
        else {
            $("#custom_due_date").hide();
        }
    });


    $("#days_after").change(function () {
        selected = $(this).val();
        if (selected === "-1") {
            $("#custom_due_date").show();
        }
        else {
            $("#custom_due_date").hide();
        }
    });

    $('#askQuestion').on('click', function () {
        $('#modalAdditionalInfoTable').show();
        $('#modalQuestionTable').show();
        $('#question_text').html($('#questionTextarea').val());
    });

    $('#submit').on('click', function (event) {
        $('#privacy').hide();
        form_id = '#' + $('#form_id').val();
        if (form_id === "#") {
            form_id = "#submitRecord";
        }
        if ((!$('#modalAdditionalInfoTable').is(':visible') && !$('#edit_email').is(':visible')) || $(form_id) == 'note_pdf') {
            $('#confirm-submit').modal('toggle');
            $(form_id).submit();
        }
        else {
            $('#modalAdditionalInfoTable').hide();
            $('#editAgencyDescription').hide();
            additional_information = $('#additional_note').val();
            var input = $("<input>")
                .attr("type", "hidden")
                .attr("name", "additional_information").val(additional_information);
            $(form_id).append($(input));

            if (CKEDITOR.instances.email_text) {
                email_text = CKEDITOR.instances.email_text.getData();
                email_text = email_text.replace('&lt', '<').replace('&gt', '>');
                email_text = email_text.replace('&#34;', '"');
                console.log(email_text);
                var emailInput = $("<input>")
                    .attr("type", "hidden")
                    .attr("name", "email_text").val(email_text);

                if ($('#addSingleEmailAttachment').is(':checked')) {
                    var attachSingleEmailAttachment = $("<input>")
                        .attr("type", "hidden")
                        .attr("name", "attach_single_email_attachment").val("true");
                    $(form_id).append(attachSingleEmailAttachment);
                }
                $(form_id).append($(emailInput));
            }
            var privacyInput;
            if (sessionStorage.getItem("switch_privacy")) {
                privacyInput = sessionStorage.getItem("switch_privacy");
            }
            else if ($('#release_and_public').is(':checked')) {
                // privacyInput = $('#release_and_public').val();
                privacyInput = "release_and_public";
            }
            else if ($('#release_and_private').is(':checked')) {
                privacyInput = "release_and_private";
            }
            else {
                privacyInput = "private";
            }

            var privacy = $("<input>").attr("type", "hidden").attr("name", "record_privacy").val(privacyInput);

            // if ($('#release_and_public[name="privacy_setting"]').attr('checked','checked')) {
            //     switch_privacy = "release_and_public";
            // } else if ($('#release_and_private[name="privacy_setting"]').attr('checked','checked')) {
            //     switch_privacy = "release_and_private";
            // } else {
            //     switch_privacy = "private";
            // }
            //
            // var switch_privacy_input = $("<input>").attr("type", "hidden").attr("name", "privacy_setting").val(switch_privacy);

            if (form_id === '#submitRecord') {
                $(form_id).append($(privacy));
                sessionStorage.clear();
                $(form_id).submit();
            }
            else {
                $(form_id).append($(privacy));
                sessionStorage.clear();
                $(form_id).submit();
            }

        }

    });

    $('#submitAgencyDescription').on('click', function (event) {
        form_id = '#' + $('#form_id').val();
        if (!$('#modalAdditionalInfoTable').is(':visible') || $(form_id) == 'note_pdf') {
            $('#confirm-submit').modal('toggle');
            $(form_id).submit();
        }
        else {
            additional_information = $('#additional_note').val();

            var input = $("<input>")
                .attr("type", "hidden")
                .attr("name", "additional_information").val(additional_information);
            $(form_id).append($(input));
            $(form_id).submit();
        }

    });

    $('#cancelDescription').on('click', function (event) {
        $('#editAgencyDescription').hide();
        $('#additionalInformation').show();
        form_id = '#' + $('#form_id').val();
        additional_information = "";
        var input = $("<input>")
            .attr("type", "hidden")
            .attr("name", "additional_information").val(additional_information);
        $(form_id).append($(input));
        $(form_id).submit();
    });

    $('#cancel_close').on('click', function (event) {
        $('#close-reminder').hide();
    });

    $('#rerouteButton').on('click', function () {
        var formData = new FormData($("#AcknowledgeNote")[0]);
        if ($("#rerouteReason").val()) {

        }
        else {
            $.ajax({
                url: "/email/email_acknowledgement.html",
                type: 'POST',
                processData: false,
                contentType: false,
                data: formData,
                success: function (data) {
                    $('#form_id').val('AcknowledgeNote');
                    var modalQuestion = 'Are you sure you want to acknowledge the request for the number of days below and send an email to the requester?';
                    modalQuestion += ' ' + $('#acknowledge_status').val();
                    $('#modalquestionDiv').html(modalQuestion);
                    $('#modalQuestionTable').hide();
                    CKEDITOR.replace('email_text');
                    $('#email_text').val(data);
                    $('#emailTextTable').hide();
                    $('#modalquestionDiv').text(modalQuestion);
                    $('#modalQuestionTable').hide();
                },
                error: function (data) {
                    alert('fail.');
                }
            });
        }
    });

    $('#extendButton').on('click', function () {

        var formData = new FormData($("#extension")[0]);
        $.ajax({
            url: "/email/email_extension.html",
            type: 'POST',
            processData: false,
            contentType: false,
            data: formData,
            success: function (data) {
                $('#form_id').val('extension');
                days = $('#days_after').val();
                var modalQuestion = 'Are you sure you want to request an extension for the number of days below and send an email to the requester?';

                if (days != -1) {
                    modalQuestion += '<br><br>' + $('#days_after').val() + " days";
                }
                else {
                    due_date = $('#datepicker').datepicker('getDate');
                    day = due_date.getDate();
                    month = due_date.getMonth() + 1;
                    year = due_date.getFullYear();

                    modalQuestion = 'Are you sure you want to set the following due date and send an email to the requester?';
                    modalQuestion += '<br><br>' + month + "/" + day + "/" + year;
                }
                CKEDITOR.replace('email_text');
                $('#email_text').val(data);
                $('#emailTextTable').hide();
                $('#modalquestionDiv').html(modalQuestion);
                $('#modalQuestionTable').hide();
            },
            error: function (data) {
                alert('fail.');
            }
        });
    });

    $('#closeButton').on('click', function () {
        var formData = new FormData($("#closeRequest")[0]);

        $.ajax({
            url: "/email/email_closed.html",
            type: 'POST',
            processData: false,
            contentType: false,
            data: formData,
            success: function (data) {
                var selectedCloseReason = $('#close_reasons option:selected').text();
                if (selectedCloseReason.indexOf('Denied') >= 0) {
                    $('#deny_explain_why').show();
                }
                else {
                    $('#deny_explain_why').hide();
                }

                $('#modalAdditionalInfoTable').hide();
                $('#close-reminder').show()
                //$('#modalAdditionalInfoTable').append('<p><b>If you are denying this request please explain why.</b></p>');
                $('#form_id').val('closeRequest');
                var modalQuestion = 'Are you sure you want to close the request for the reasons below and send an email to the requester?';
                var reasons = $('#close_reasons').val();
                modalQuestion += '<br><br>';
                var i;
                for (i = 0; i < reasons.length; i++) {
                    modalQuestion += '<br><br>' + reasons[i];
                }
                CKEDITOR.replace('email_text');
                $('#email_text').val(data);
                document.getElementById("edit_email").style.visibility = "visible";
                $('#emailTextTable').hide();
                $('#modalquestionDiv').html(modalQuestion);
                $('#modalQuestionTable').hide();
            },
            error: function (data) {
                alert('fail.');
            }
        });
    });

    $('#editAgencyDescriptionButton').on('click', function () {
        $('#modalAdditionalInfoTable').show();
        $("#edit-agency-description").toggle();
        var modalQuestion = 'Type in the agency description below';
        modalQuestion += '<br><br>';
        $('#form_id').val('agency_description');
        $('#modalquestionDiv').html(modalQuestion);
        $('#modalQuestionTable').hide();
    });

    $('#file_upload_filenames').bind('DOMNodeInserted', function (event) {
        var names = [];
        if ($("input[name=record]") && $("input[name=record]").get(0) && $("input[name=record]").get(0).files) {
            for (var i = 0; i < $("input[name=record]").get(0).files.length; ++i) {
                names.push($("input[name=record]").get(0).files[i].name);
            }
        }

        if (names.length > 4) {
            $('#close_filenames_list').click();
            $('#numFiles').show();
        }
        else {
            $('#file_upload_one').text(names[0]);
            $('#file_upload_two').text(names[1]);
            $('#file_upload_three').text(names[2]);
            $('#file_upload_four').text(names[3]);
            $('#numFiles').hide();
        }

    });

    $('.privacy_radio').on('click', function () {
        console.log("Changing privacy");
        if (this.id === "release_and_public" || this.id === "release_and_private") {
            var privacy_setting = this.id.toString();
            var $this = $(this);
            var csrf_token = $this.prev().prev().prev().val();
            var request_id = $this.prev().prev().val();
            var record_id = $this.prev().val();
            if (privacy_setting === "release_and_private") {
                csrf_token = $this.prev().prev().prev().prev().val();
                request_id = $this.prev().prev().prev().val();
                record_id = $this.prev().prev().val();
            }
            var filePath = $this.parent().prev().children();
            var filePathArray = filePath[0].toString().split('/');
            var fileName = filePathArray[filePathArray.length - 1];

            var modalQuestion = 'Are you sure you want to make this record public and send an email to the requester? ' + fileName;

            $('#modalquestionDiv').text(modalQuestion);
            $('#modalQuestionTable').hide();
            $('#confirm-submit').modal('toggle');

            $.ajax({
                url: "/switchRecordPrivacy",
                type: 'POST',
                data: {
                    _csrf_token: csrf_token,
                    privacy_setting: privacy_setting,
                    request_id: request_id,
                    record_id: record_id
                },
                success: function (data) {
                    console.log("DONE");
                    if ($('#release_and_public[name="privacy_setting"]').attr('checked', 'checked')) {
                        switch_privacy = "release_and_public";
                    } else if ($('#release_and_private[name="privacy_setting"]').attr('checked', 'checked')) {
                        switch_privacy = "release_and_private";
                    } else {
                        switch_privacy = "private";
                    }
                    sessionStorage.setItem("switch_privacy", switch_privacy);
                    $.ajax({
                        url: "/email/email_city_response_added.html",
                        type: 'POST',
                        data: {
                            _csrf_token: csrf_token,
                            privacy_setting: switch_privacy,
                            request_id: request_id,
                            record_id: record_id
                        },
                        success: function (data) {
                            CKEDITOR.replace('email_text');
                            if (fileName) {
                                data = data + ' filename:' + fileName;
                            }
                            $('#email_text').val(data);
                            $('#modalquestionDiv').text(modalQuestion);
                            $('#modalQuestionTable').hide();
                        },
                        error: function (data) {
                            alert('fail.');
                        }
                    });
                    /*$('#modalAdditionalInfoTable').show();
                     $('#form_id').val('submitRecord');
                     var modalQuestion = 'Are you sure you want to make this record public and send an email to the requester?';
                     modalQuestion += $('#recordSummary').text();
                     modalQuestion += "<br>";*/
                    //CKEDITOR.replace( 'email_text' );
                    //$('#email_text').val(data);
                    //$('#emailTextTable').hide();
                    //$('#modalquestionDiv').text(modalQuestion);
                    //$('#modalQuestionTable').hide();
                },
                error: function (data) {
                    alert('fail.');
                }
            });

            //$('#addRecordButton').click();
        }
    });

    $('#close_filenames_list').on('click', function () {
        $('#file_upload_one').empty();
        $('#file_upload_two').empty();
        $('#file_upload_three').empty();
        $('#file_upload_four').empty();
    });


    $('#addRecordButton').on('click', function () {
        $('#privacy').show();
        var formData = new FormData($("#submitRecord")[0]);
        $('#submit').hide();
        $.ajax({
            url: "/email/email_city_response_added.html",
            type: 'POST',
            processData: false,
            contentType: false,
            data: formData,
            success: function (data) {
                $('#submit').show();
                $('#modalAdditionalInfoTable').hide();
                $('#form_id').val('submitRecord');
                var modalQuestion = 'Are you sure you want to add this record and send an email to the requester?';
                modalQuestion += $('#recordSummary').text();
                $('#modalquestionDiv').text(modalQuestion);
                $('#modalQuestionTable').hide();
                CKEDITOR.replace('email_text');
                $('#email_text').val(data);
                $('#emailTextTable').hide();
                $('#modalquestionDiv').text(modalQuestion);
                $('#modalQuestionTable').hide();

                // setTimeout(wait, 5000);
            },
            error: function (data) {
                alert('fail.');
            }
        });
    });

    $('#edit_email').on('click', function () {
        for (var editorInstance in CKEDITOR.instances) {
            CKEDITOR.instances[editorInstance].setReadOnly(false);
        }
    });

    //Check if all the required fields are filled out.
    $("[data-toggle='modal']").click(function (e) {
        if (this.id === "addRecordButton") {
            var titleTexts = $('.title_text');
            $('.title_text').each(function () {
                if ($(this).val() === '') {
                    $('#missing_title').show();
                    $('#missing_title').focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
            if ($('.title_text').val() == null)
            {
                if ($('#recordSummary').val() == '' && $('#inputUrl').val() == '' && $('#offlineDoc_textarea').val() == '') {
                    $('#missing_field').show();
                    $('#missing_field').focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                else if ($('#recordSummary').val() == ''){
                    $('#missing_record_name').show();
                    $('#missing_record_name').focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                else if ($('#inputUrl').val() == '' && $('#offlineDoc_textarea').val() ==''){
                    $('#missing_access').show();
                    $('#missing_access').focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
            }
        }
    });

    $('#addNoteButton').on('click', function () {
        $('#emailTextTable').hide();
        $('#email_text').hide();
        document.getElementById("edit_email").style.visibility = "hidden";
        $('#cke_email_text').hide();
        $('#modalAdditionalInfoTable').hide();
        $('#form_id').val('note');
        var modalQuestion = 'Are you sure you want to add the note below?';
        modalQuestion += '<br><br>' + $('#noteTextarea').val();
        $('#modalquestionDiv').html(modalQuestion);
        $('#modalQuestionTable').hide();
    });

    $('#addPublicNoteButton').on('click', function () {
        $('#modalAdditionalInfoTable').hide();
        $('#form_id').val('note');
        var modalQuestion = 'Are you sure you want to add the note below to this request?';
        modalQuestion += '<br><br>' + $('#noteTextarea').val();
        $('#modalquestionDiv').html(modalQuestion);
        $('#modalQuestionTable').hide();
    });

    $('#generatePDFButton').on('click', function (event) {
        $('#emailTextTable').hide();
        $('#email_text').hide();
        $('#edit_email').style.visibility = "hidden";
        var selectedTemplate = $('#response_template option:selected').text();
        var modalQuestion = 'Are you sure you want to generate a Word Document for the template below?';

        if (selectedTemplate === '') {
            $('#missing_pdf_template').removeClass('hidden');
        }
        else {
            if (selectedTemplate === 'Deny Request' || selectedTemplate === 'Partial Denial of Request') {
                $('#deny_explain_why').show();
            }
            else {
                $('#deny_explain_why').hide();
            }
            $('#missing_pdf_template').addClass('hidden');
            var attr = $('#generatePDFButton').attr('data-toggle');
            $('#generatePDFButton').attr('data-toggle', 'modal');
            $('#generatePDFButton').attr('data-target', '#confirm-submit');

            $('#modalAdditionalInfoTable').hide();
            $('#form_id').val('note_pdf');
            modalQuestion += '<br><br>' + selectedTemplate;
            $('#modalquestionDiv').html(modalQuestion);
            $('#modalQuestionTable').hide();
        }


    });

    $('#notifyButton').on('click', function () {
        $('#form_id').val('notifyForm');
        var modalQuestion = 'Are you sure you want to add the helper and send an email to the requester? Please specify the reason below.';
        modalQuestion += '<br><br>' + $('#notifyReason').val();
        $('#modalquestionDiv').html(modalQuestion);
        $('#modalQuestionTable').hide();
    });

    $("#requesterInfoButton").on('click', function () {
        $('#requester_info').toggle();
        if ($('#requester_info').is(':visible')) {
            $('#requesterInfoButton').html("Hide Requester Contact Information &#9650;");
        } else {
            $('#requesterInfoButton').html("Show Requester Contact Information &#9660;");
        }
    });

    $('#requesterEditButton').on('click', function () {

    });

    $(".start").on('click', function () {
        var title = $('.title_text');
        var titleLengthCorrect = 1;

        $.each(title, function (index, t) {
            if (t.value.length > 140) {
                $('#record_title_alert').show();
                titleLengthCorrect = -1;
            }
        });

        if (titleLengthCorrect === 1) {
            $('#record_title_alert').hide();
            $('#addRecordButton').click();
        }
    });

    $("#cancel_all").on('click', function () {
        $('.delete').click();
    });

    $("#cancel").on('click', function () {
        $('#privacy').hide();
        $('.additional-note').show();
        $('#emailTextTable').show();
        document.getElementById("edit_email").style.visibility = "visible";
        // $('#edit_email').hide();
        $('#modalAdditionalInfoTable').hide();
        // $('#edit_email').show();
        $('#email_text').hide();
    });

    $('#addNoteButton').prop('disabled', true);
    $('#noteTextarea').keyup(function () {
        $('#addNoteButton').prop('disabled', this.value == "" ? true : false);
    })

    $("#datepicker").datepicker();
    /*$(document).on('ready', function() {
     $("#record").fileinput({
     maxFileCount: 4,
     validateInitialCount: true,
     overwriteInitial: false,
     allowedFileExtensions: ["txt", "pdf", "doc", "rtf", "odt", "odp", "ods", "odg","odf","ppt", "pps", "xls", "docx", "pptx", "ppsx", "xlsx","jpg","jpeg","png","gif","tif","tiff","bmp","avi","flv","wmv","mov","mp4","mp3","wma","wav","ra","mid"]
     });
     });*/
})($);


