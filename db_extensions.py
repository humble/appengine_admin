from google.appengine.api.datastore_errors import BadValueError
from google.appengine.ext import db


class StringListChoicesProperty(db.StringListProperty):
  '''Validate StringListProperty for allowed choices.'''

  def validate(self, value):
    '''Check the submitted values are valid choices.'''
    # Prevent appengine from enforcing it's single-choice validation.
    # Allow multiple choice.
    choices = self.choices
    self.choices = []
    value = super(StringListChoicesProperty, self).validate(value)
    self.choices = choices

    # Specific validation for choices
    if not self.empty(value):
      for item in value:
        if item not in self.choices:
          raise BadValueError('Allowed values for %s: %s' %
                              (self.name, self.choices))
    return value
