from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader

img = '/vagrant/app/static/img/nyc_seal_letterhead.png'

im = Image(img, 1*inch, 1*inch)

ENVELOPE = (4.125*inch, 9*inch)

c = canvas.Canvas("hello.pdf", pagesize=landscape(ENVELOPE))
c.drawString(324, 280, "Welcome to Reportlab!")
c.drawImage(img, 10, 80, 1.5*inch, preserveAspectRatio=True)
c.save()


def get_image(path, width=1*inch):
    """
    Create a reportlab.platypus.Image object with the proper size based on the aspect ratio of the original image and
    the provided width.

    :param path: Filepath to the image.
    :param width: Width of the final Image object in points (defaults to 72 points)
    :return: reportlab.platypus.Image
    """

    img = ImageReader(path)
    img_width, img_height = img.getSize()
    aspect_ratio = img_height / float(img_width)
    return Image(path, width=width, height=(width*aspect_ratio))

