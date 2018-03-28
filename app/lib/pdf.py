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
