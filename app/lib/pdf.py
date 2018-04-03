from flask_weasyprint import render_pdf, HTML


def generate_pdf(pdf_data):
    """
    Generate a PDF from a string of data.
    :param pdf_data: String of data to input into PDF.
    :return: PDF object
    """

    html = HTML(string=pdf_data)
    f = html.write_pdf()

    return f


def generate_pdf_flask_response(pdf_data):
    """
    Return a Flask response object with a PDF as an attachment.
    :param pdf_data: String of data to input into PDF.
    :return: Flask Response
    """
    html = HTML(string=pdf_data)

    return render_pdf(html)
