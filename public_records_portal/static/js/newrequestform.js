$(function () {
    var business = [
            "Department of Consumer Affairs",
            "Mayor's Office of Contract Services",
            "Procurement Policy Board",
            "Small Business Services"
    ]
    var cultureAndRecreation = [
            "Art Commission",
            "Department of Cultural Affairs",
            "Mayor's Office of Media and Entertainment",
            "Department of Parks and Recreation"
    ]
    var education = [
        "Department of Education",
        "School Construction Authority"
    ]
    var environment = [
        "Department of Environmental Protection",
        "Department of Sanitation",
        "Office of Environmental Remediation",
        "Office of Long-Term Planning & Sustainability"
    ]
    var governmentAdministration = [
        "Board of Elections",
        "Business Integrity Commission",
        "City Commission on Human Rights",
        "Civil Service Commission",
        "Conflicts of Interest Board",
        "Department of Citywide Administrative Services",
        "Department of Design and Construction",
        "Department of Finance",
        "Department of Information Technology and Telecommunications",
        "Department of Records and Information Services",
        "Design Commission",
        "Equal Employment Practices Commission",
        "Financial Information Services Agency",
        "Law Department",
        "Office of Administrative Trials and Hearings",
        "Office of Labor Relations",
        "Office of Management and Budget",
        "Office of Payroll Administration",
        "Office of the Actuary",
        "Office of the Mayor"
    ]
    var health = [
        "Department of Health and Mental Hygiene",
        //"Health and Hospitals Corporation",
        "Office of the Chief Medical Examiner"
    ]
    var housingAndDevelopment = [
        "Board of Standards and Appeals",
        "Department of Buildings",
        "Department of City Planning",
        "Housing Recovery Operations",
        "Landmarks Preservation Commission",
        "Loft Board",
        "New York City Housing Authority",
        "New York City Housing Development Corporation"
    ]
    var publicSafety = [
        "Board of Correction",
        "Civilian Complaint Review Board",
        "Commission to Combat Police Corruption",
        "Department of Correction",
        "Department of Investigation",
        "Department of Probation",
        "New York City Fire Department",
        "NYC Emergency Management",
        "Office of the Special Narcotics Prosecutor",
        "Police Department"
    ]
    var socialServices = [
        "Administration for Children's Services",
        "Department for the Aging",
        "Department of Homeless Services",
        "Department of Housing Preservation and Development",
        "Department of Youth and Community Development",
        "Human Resources Administration",
        "Office of Collective Bargaining"

    ]
    var transportation = [
        "Department of Transportation",
        "Taxi and Limousine Commission"
    ]

    $("#category_info").tooltip();

    $("#agency").ready(function () {
        vals = [];
        vals = business.concat(cultureAndRecreation, education, environment, governmentAdministration,
            health, housingAndDevelopment, publicSafety, socialServices, transportation);
        vals.sort();

        for (var i = 0; i < vals.length; i++) {
            if (vals[i]==($("#agency option:selected").text())){
                continue;
            }
            else{
                $("#agency").value = vals[i];
                $("#agency").append("<option value=\"" + vals[i] + "\">" + vals[i] + "</option>");
            }
        }
    });

    $("#category").change(function () {
        var $dropdown = $(this);
        var key = $dropdown.val();
        var vals = [];

        switch (key) {
            case 'Business':
                vals = business;
                break;
            case 'Culture and Recreation':
                vals = cultureAndRecreation;
                break;
            case 'Education':
                vals = education;
                break;
            case 'Environment':
                vals = environment;
                break;
            case 'Government Administration':
                vals = governmentAdministration;
                break;
            case 'Health':
                vals = health;
                break;
            case 'Housing':
                vals = housingAndDevelopment;
                break;
            case 'Public':
                vals = publicSafety;
                break;
            case 'Social Services':
                vals = socialServices;
                break;
            case 'Transportation':
                vals = transportation;
                break;
            default:
                vals = [];
                vals = business.concat(cultureAndRecreation, education, environment, governmentAdministration,
                    health, housingAndDevelopment, publicSafety, socialServices, transportation);
                break;
        }

        var $jsontwo = $("#agency");

        $jsontwo.empty();
        vals.sort();
        if (vals[0] === "") {
        } else {
            vals.splice(0, 0, "");
        }
        for (var i = 0; i < vals.length; i++) {
            if (vals[i] == vals[i-1]) {
                continue;
            }
            $jsontwo.value = vals[i];
            $jsontwo.append("<option value=\"" + vals[i] + "\">" + vals[i] + "</option>");
        }
        ;
    });

});

$(function () {
    // displays characters remaining
    function maxLength(el) {
        if (!('maxLength' in el)) {
            var max = el.attr('maxlength');
            el.onkeypress = function () {
                if (this.value.length >= max) return false;
            };
        }
    }

    var request_summary_max_length = $('#request_summary').attr('maxlength');

    // displays characters remaining
    $('#request_summary_counter').text(request_summary_max_length + ' characters remaining');

    $('#request_summary').keyup(function () {
        var text_length = $('#request_summary').val().length;
        var text_remaining = request_summary_max_length - text_length;
        $('#request_summary_counter').text(text_remaining + ' characters remaining');
        console.log(text_remaining);
        if (text_remaining <= 0) {
            document.getElementById("request_summary_counter").style.color = "red";
        } else {
            document.getElementById("request_summary_counter").style.color = "black";
        }
    });

    var request_description_max_length = $('#request_text').attr('maxlength');

    // displays characters remaining
    $('#request_description_counter').html(request_description_max_length + ' characters remaining');

    $('#request_text').keyup(function () {
        var text_length = $('#request_text').val().length;
        var text_remaining = request_description_max_length - text_length;
        $('#request_description_counter').html(text_remaining + ' characters remaining');
        if (text_remaining <= 0) {
            document.getElementById("request_description_counter").style.color = "red";
        } else {
            document.getElementById("request_description_counter").style.color = "black";
        }
    });
});
