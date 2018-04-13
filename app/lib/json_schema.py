from jsonschema import validate, ValidationError
from flask import current_app
import json
import os
from app import sentry


def validate_schema(data, schema_name):
    """
    Validate the provided data against the provided JSON schema.

    :param data: JSON data to be validated
    :param schema_name: Name of the schema 
    :return: Boolean
    """
    with open(os.path.join(current_app.config['JSON_SCHEMA_DIRECTORY'], schema_name + '.schema'), 'r') as fp:
        schema = json.load(fp)

        try:
            validate(data, schema)
            return True
        except ValidationError as e:
            sentry.captureException()
            current_app.logger.info("Failed to validate {}\n{}".format(json.dumps(data), e))
            return False
