from io import StringIO

from xhtml2pdf import pisa

from app import sentry
from app.lib.utils import PDFCreationException


def create_pdf(pdf_data):
    """
    Generate a PDF from a string of data.
    :param pdf_data: String of data to input into PDF.
    :return: PDF object
    """
    # Create the StringIO Object that will hold the PDF
    pdf = StringIO()

    # Use xhmtl2pdf to create the PDF and store it in the StringIO Object
    pisa_status = pisa.CreatePDF(src=pdf_data.encode('utf-8'), dest=pdf)

    # Store the PDF Data
    resp = pdf.getvalue()

    # Close the StringIO Object
    pdf.close()

    # If there is an error, raise an exception "PDFCreationException"
    if not pisa_status.err:
        raise PDFCreationException(pisa_status)
    return resp
