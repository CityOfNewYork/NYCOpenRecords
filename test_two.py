#!/usr/bin/env python

from pylatex import Document, Section, Subsection, Package, Command
from pylatex.utils import italic, NoEscape


def fill_document(doc):
    """Add a section, a subsection and some text to the document.

    :param doc: the document
    :type doc: :class:`pylatex.document.Document` instance
    """

    pass


if __name__ == '__main__':
    # Basic document
    doc = Document('basic')
    doc.documentclass = Command(
        'documentclass',
        options=['12pt', 'landscape'],
        arguments=['article'],
    )
    fill_document(doc)
    doc.packages.append(Package('geometry',
                                options=['left=.2in', 'top=0.15in', 'papersize={4.12in,9.50in}', 'landscape',
                                         'twoside=false']))
    doc.generate_pdf(clean_tex=False)
    doc.generate_tex()
