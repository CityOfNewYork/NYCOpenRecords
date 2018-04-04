from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from collections import namedtuple

Dimensions = namedtuple('ImageDimensions', ['width', 'height'])


def get_image(path, width=1 * inch):
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
    return Image(path, width=width, height=(width * aspect_ratio))


def get_image_dimensions(path, width=1 * inch):
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
    return Dimensions(width=width, height=(width * aspect_ratio))


def _position_top_left(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the top left of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = margin
    base_y = max(dimensions.height, page_size.height / 2)
    y_coord = dimensions.height - dimensions.height / 2

    return x_coord, y_coord


def _position_top_center(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the top center of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = (page_size.width / 2) - (dimensions.width / 2)
    base_y = max(dimensions.height, page_size.height / 2)
    y_coord = base_y - dimensions.height

    return x_coord, y_coord


def _position_top_right(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the top right of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = page_size.width - (dimensions.width + margin)
    base_y = max(dimensions.height, page_size.height / 2)
    y_coord = base_y - dimensions.height

    return x_coord, y_coord


def _position_middle_left(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the middle left of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = margin
    y_coord = 0

    return x_coord, y_coord


def _position_middle_center(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the middle center of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = (page_size.width / 2) - (dimensions.width / 2)
    y_coord = 0

    return x_coord, y_coord


def _position_middle_right(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the middle right of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = page_size.width - (dimensions.width + margin)
    y_coord = 0

    return x_coord, y_coord


def _position_bottom_left(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the bottom left of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = margin
    y_coord = 0 - (page_size.height / 2) + (dimensions.height / 2)

    return x_coord, y_coord


def _position_bottom_center(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the bottom center of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = (page_size.width / 2) - (dimensions.width / 2)
    y_coord = 0 - (page_size.height / 2) + (dimensions.height / 2)

    return x_coord, y_coord


def _position_bottom_right(page_size, dimensions, margin=10):
    """
    Provide the x and y coordinates for an object positioned in the bottom right of the page.

    :param page_size: Size of the page (Width, Height) as a tuple (in points)
    :param dimensions: Dimensions of the object (Dimension Object)
    :return:
    """
    x_coord = page_size.width - (dimensions.width + margin)
    y_coord = 0 - (page_size.height / 2) + (dimensions.height / 2)
    return x_coord, y_coord


def calculate_location(dimensions: Dimensions, page_size: Dimensions, location: str) -> tuple:
    """
    Determine the exact location (in points) for a reportlab object).
    :param dimensions: Dimension object (named tuple with Width and Height) - Describes size of object
    :param page_size: Dimension object (named tuple with Width and Height) - Describes size of page
    :param location: One of ('top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right',
                     'bottom-left', 'bottom-center', 'bottom-right')
    :return: (x_coord, y_coord)
    """
    location_dict = {
        'top-left': _position_top_left,
        'top-center': _position_top_center,
        'top-right': _position_top_right,
        'middle-left': _position_middle_left,
        'middle-center': _position_middle_center,
        'middle-right': _position_middle_right,
        'bottom-left': _position_bottom_left,
        'bottom-center': _position_bottom_center,
        'bottom-right': _position_bottom_right,
    }
    tmp = location_dict[location](page_size, dimensions)
    print(tmp)
    return tmp


img = '/vagrant/app/static/img/nyc_seal_letterhead.png'

im = Image(img, 1 * inch, 1 * inch)

ENVELOPE = Dimensions(9 * inch, 4.125 * inch)
c = canvas.Canvas("hello.pdf", pagesize=landscape(ENVELOPE))

dimensions = get_image_dimensions(img, ENVELOPE[1] / 2)
im_x, im_y = calculate_location(dimensions, ENVELOPE, 'top-left')
c.drawInlineImage(img, x=im_x, y=im_y, width=ENVELOPE[1] / 2,
                  preserveAspectRatio=True)

envelope_footer_part_1 = 'FOR POLICE'
c.drawString()

c.save()
