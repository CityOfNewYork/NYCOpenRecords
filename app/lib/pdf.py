from flask import current_app
from flask_weasyprint import render_pdf, HTML
import jinja2
import subprocess

import os
from tempfile import gettempdir, _get_candidate_names

from app.constants.pdf import LATEX_TEMPLATE_CONFIG
from app.lib.utils import PDFCreationException


class LatexCompiler:
    """
    Generates a PDF from a LaTeX file.

    Slightly modified from: https://github.com/AKuederle/flask-template-master/
    """
    LATEX_COMMAND = 'pdflatex -interaction=nonstopmode'
    FILE_EXTENSION = 'pdf'

    _OUT_DIR = gettempdir()

    def __init__(self, latex_command=None):
        self.LATEX_COMMAND = latex_command or self.LATEX_COMMAND
        self._TEMP_OUT_NAME = next(_get_candidate_names())

    def _create_file(self, document):
        temp_file = os.path.join(self._OUT_DIR, self._TEMP_OUT_NAME)
        temp_tex = temp_file + '.tex'
        with open(temp_tex, 'wb') as f:
            f.write(document.encode('utf-8'))
        proc = subprocess.Popen([*self.LATEX_COMMAND.split(' '), temp_tex], cwd=self._OUT_DIR, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return_code = proc.wait()
        out, err = proc.communicate()
        if return_code != 0:
            raise PDFCreationException(status_code=return_code, stdout=out, stderr=err)  # TODO: Make this a proper error

        data = None
        with open('{filename}.{extension}'.format(filename=temp_file, extension=self.FILE_EXTENSION), 'rb') as f:
            data = f.read()

        os.remove('{filename}.{extension}'.format(filename=temp_file, extension=self.FILE_EXTENSION))
        os.remove(temp_tex)

        return data

    def compile(self, document):
        """
        Compile a LaTeX document to PDF.
        :param document: LaTeX formatted document (UTF-8 Formatted String)
        :return: PDF File Object
        """
        file = self._create_file(document)
        return file


def generate_pdf(pdf_data):
    """
    Generate a PDF from a string of data.
    :param pdf_data: String of data to input into PDF.
    :return: PDF File object
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


def generate_envelope(template_name, data):
    """
    Generate the LaTeX for an envelope with the provided data pre-filled.

    :param template_name: The LaTeX template to be used.
    :param data: Data to be filled in to the LaTeX template (Dict())
    :return: LaTeX document
    """
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(current_app.config['LATEX_TEMPLATE_DIRECTORY']),
                                     **LATEX_TEMPLATE_CONFIG)
    document = environment.get_template(template_name + '.tex').render(**data)

    return document


def generate_envelope_pdf(document):
    """
    Generate a PDF envelope.
    :param document: LaTeX document.
    :return: PDF File Object
    """
    compiler = LatexCompiler()

    return compiler.compile(document)


def escape_latex_characters(line):
    """
    Replace a string with the escaped LaTeX version of reserved characters
    :param line: a string to be used in a LaTeX template
    :return: a string with the escaped LaTeX version of reserved characters
    """
    line = line.replace('\\', '\\textbackslash')
    line = line.replace('&', '\&')
    line = line.replace('%', '\%')
    line = line.replace('$', '\$')
    line = line.replace('#', '\#')
    line = line.replace('_', '\_')
    line = line.replace('{', '\{')
    line = line.replace('}', '\}')
    line = line.replace('~', '\\textasciitilde')
    line = line.replace('^', '\\textasciicircum')
    return line
