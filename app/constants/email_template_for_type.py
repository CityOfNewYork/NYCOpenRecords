from app.constants import response_type, determination_type


def template(resp_type):
    return {
        response_type.FILE: "email_response_file.html",
        response_type.LINK: "email_response_link.html",
        response_type.NOTE: "email_response_note.html",
        response_type.INSTRUCTIONS: "email_response_instruction.html",
        determination_type.ACKNOWLEDGMENT: "email_response_acknowledgment.html",
        determination_type.DENIAL: "email_response_denial.html",
        determination_type.CLOSING: "email_response_closing.html"
    }[resp_type]
