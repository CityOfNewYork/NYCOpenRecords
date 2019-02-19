This will walk you through how to set up custom request forms for OpenRecords.

First, add the custom_request_forms key/value pair into an agency's agency_features JSON. Below is an example:

```
"custom_request_forms": {
  "enabled": false,
  "categorized": false,
  "expand_by_default": false,
  "category_info_text": "",
  "category_warning_text": "",
  "multiple_request_types": false,
  "description_hidden_by_default": true
}
```

- `enabled` will determine if that agency's custom request forms are turned on or not. This value can be true or false.
- `categorized` will determine if the forms are categorized.When forms are categorized only one category of form can be submitted.
- `expand_by_default` will determine if the custom form panels on the view request page are expanded or not by default.
- `category_info_text` adds text on the new request page to give information about how an agency's form are categorized.
- `category_warning_text` adds text to the modal that pops up when a user attempts to select a form of a different category.
- `multiple_request_types` determines if multiple custom forms can be submitted as part of a single request.
- `description_hidden_by_default` determines if the request description is visible on the view request page. When custom forms are enabled the request description is replaced by a list of the custom request form names in that request. Ex) Arrest Report, Body Worn Camera, Incident Report

To build a form append a JSON to the `custom_request_forms.json` inside the array of the key `custom_request_forms`. Below is an example of a custom form:

```
{
  "agency_ein": "0056",
  "form_name": "NYPD Test Form",
  "form_description": "",
  "field_definitions": [
    {
      "Input Test": {
        "type": "input",
        "name": "input-test",
        "required": false
      }
    },
    {
      "Textarea Test": {
        "type": "textarea",
        "name": "textarea-test",
        "required": false,
        "max_length": "50",
        "character_counter": true
      }
    },
    {
      "Date Test": {
        "type": "date",
        "name": "date-test",
        "required": false
      }
    },
    {
      "Time Test": {
        "type": "time",
        "name": "time-test",
        "required": false
      }
    },
    {
      "Dropdown Test": {
        "type": "select_dropdown",
        "name": "dropdown-test",
        "values": [
          "option1",
          "option2",
          "option3"
        ],
        "required": false
      }
    },
    {
      "Radio Test": {
        "type": "radio",
        "name": "radio-test",
        "help_text": "Please select an option",
        "values": [
          "option1",
          "option2",
          "option3"
        ],
        "required": false
      }
    },
    {
      "Select Multiple Test": {
        "type": "select_multiple",
        "name": "select-multiple-test",
        "values": [
          "option1",
          "option2",
          "option3"
        ],
        "required": false
      }
    }
  ],
  "repeatable": "5",
  "category": "1",
  "minimum_required": "2"
}
````

- `agency_ein` is the ein of the agency the form belongs to.
- `form_name` is the name of the form that will display in the Request Type dropdown.
- `form_description` is used as a short description of the form that will appear at the top when the form is selected.
- `field_definitions` is an array that holds each indivisual field in the form along with its properties.
- `repeatable` determines how many times a form can be repeated if `multiple_request_types` is enabled.
- `category` is the category of the form is `categorized` is enabled.
- `minimum_required` is a validator that sets the minumum number of fields that are required to be completed in order for the form to be successfully submitted.

Here are the possible fields that can be placed into the `field_definitons` array:

Input
```
{
  "Input Test": {
    "type": "input",
    "name": "input-test",
    "required": false,
    "placeholder": "Input placeholder text",
    "max_length": "50",
    "min_length": "10",
    "character_counter": true,
    "help_text": "Input help text",
    "error_message": "<strong>Error, an input is required.</strong> Please type in a some text."
  }
}
```
- The key of this key/value pair will be the Displayed label of the field
- `type` is the type of that field. Here we are using `input`.
- `name` should be a unique value that will be the ID of that HTML element.
- `required` determines is the field is required or not.
- `placeholder` will appear as placeholder text in the field.
- `max_length` is the max character length of the field. This will be applied as both a parsley validator and HTML5 validator.
- `min_length` is the min character length of the field. This will be applied as both a parsley validator and HTML5 validator.
- `character_counter` adds a character counter at the bottom of the input. This field must be combined with at least a `max_length` property or else it will not work.
- `help_text` is text that will appear directly under the label of the field.
- `error_message` is the text of the error if the field fails the required validation. HTML can be used in this property.


Textarea
```
{
  "Textarea Test": {
    "type": "textarea",
    "name": "textarea-test",
    "required": false,
    "max_length": "50",
    "character_counter": true
  }
}
```
Text area can use the same properties as an Input.


Date
```
{
  "Date Test": {
    "type": "date",
    "name": "date-test",
    "required": false,
    "past_date_invalid": true,
    "current_date_invalid": true
  }
}
```
Date can only use `type`, `name`, `required`, `help_text`, `error_message`, `past_date_invalid`,
`current_date_invalid`, `future_date_invalid`.
- `past_date_invalid`, if set to true, checks that the entered date is not before the current date.
- `current_date_invalid`, if set to true, checks that the entered date is not equal to the current date.
- `future_date_invalid`, if set to true, checks that the entered date is not after the current date.


Time
```
{
  "Time Test": {
    "type": "time",
    "name": "time-test",
    "required": false
  }
}
```
Time can only use `type`, `name`, `required`, `help_text`, and `error_message`.


Dropdown
```
{
  "Dropdown Test": {
    "type": "select_dropdown",
    "name": "dropdown-test",
    "values": [
      "option1",
      "option2",
      "option3"
    ],
    "required": false
  }
}
```
Dropdown can use `type`, `name`, `required`, `help_text`, `error_message`, and `values`.
- `values` is an array of strings containing the options of the dropdown.


Radio
```
{
  "Radio Test": {
    "type": "radio",
    "name": "radio-test",
    "help_text": "Please select an option",
    "values": [
      "option1",
      "option2",
      "option3"
    ],
    "required": false
  }
}
```
Radio can use `type`, `name`, `required`, `help_text`, `error_message`, and `values`.


Select Multiple
```
{
  "Select Multiple Test": {
    "type": "select_multiple",
    "name": "select-multiple-test",
    "values": [
      "option1",
      "option2",
      "option3"
    ],
    "required": false
  }
}
```
Select Multiple can use `type`, `name`, `required`, `help_text`, `error_message`, and `values`.

To populate the `custom_request_forms` table, run the following commands:
- `python manage.py shell`
- `CustomRequestForms.populate()`

