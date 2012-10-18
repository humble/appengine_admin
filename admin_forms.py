from google.appengine.ext import db

from . import fields, wtforms
from wtforms.ext.appengine.db import ModelConverter, model_form


class WTForm(wtforms.Form):
  def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
    if self.pre_init:
      obj = self.pre_init(self, obj, formdata)
    self.instance = obj

    super(WTForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)
    if self.post_init:
      obj = self.post_init(self, obj, formdata)

  def validate(self):
    """
    Validates the form by calling `validate` on each field, passing any
    extra `Form.validate_<fieldname>` validators to the field validator.

    Override wtforms.Form behavior to add extra validators.
    """
    field_names_to_skip = []
    for name, field in self._fields.items():
      if hasattr(field, 'readonly'):
        field_names_to_skip.append(name)

    for field_name in field_names_to_skip:
      delattr(self, field_name)

    self._valid = super(wtforms.Form, self).validate(self.field_validators)
    return self._valid

  def save(self, put=True):
    if not hasattr(self, '_valid'):
      raise Exception('self.validate() not called before saving.')
    data = self.data
    model_properties = {}
    dynamic_properties = {}
    properties = self.model.properties().keys()
    for name, value in data.items():
      if name in properties:
        model_properties[name] = value
      else:
        dynamic_properties[name] = value
    instance = self.instance
    if instance:
      for name, value in model_properties.items():
        setattr(instance, name, value)
    else:
      instance = self.model(**model_properties)
    for name, value in dynamic_properties.items():
      setattr(instance, name, value)

    if self.pre_save:
      instance = self.pre_save(self, instance)

    if put:
      instance_or_result = instance.put()

      if isinstance(instance_or_result, self.model):
        instance = instance_or_result
      elif isinstance(instance_or_result, db.Key):
        instance = db.get(instance_or_result)

      if self.post_save:
        return self.post_save(self, instance)

    return instance


def convert_DateTimeProperty(model, prop, kwargs):
  """Returns a form field for a ``db.DateTimeProperty``."""
  if prop.auto_now or prop.auto_now_add:
      return None

  return fields.DateTimeField(format='%Y-%m-%d %H:%M:%S', **kwargs)


def convert_DateProperty(model, prop, kwargs):
  """Returns a form field for a ``db.DateProperty``."""
  if prop.auto_now or prop.auto_now_add:
      return None

  return fields.DateField(format='%Y-%m-%d', **kwargs)


def convert_ListProperty(model, prop, kwargs):
  """Returns a form field for a ``db.ListProperty``."""
  if prop.item_type == db.Key:
    return fields.AjaxKeyField(multiple=True,
                               object_classes=getattr(prop, 'object_classes', None),
                               **kwargs)
  # TODO fall back to textarea for int
  # And list of text areas for list of strings
  return None


def convert_ReferenceProperty(model, prop, kwargs):
  """Returns a form field for a ``db.ReferenceProperty``."""
  kwargs.setdefault('required', prop.required)
  return fields.AjaxKeyField(multiple=False,
                             object_classes=[prop.reference_class],
                             **kwargs)


class AdminConverter(ModelConverter):
  def __init__(self, model, *args, **kwargs):
    self.default_converters.update({
      'DateTimeProperty': convert_DateTimeProperty,
      'DateProperty': convert_DateProperty,
      'ListProperty': convert_ListProperty,
      'ReferenceProperty': convert_ReferenceProperty,
    })
    for prop in model.properties().values():
      if hasattr(prop, 'wtforms_convert'):
        self.default_converters[type(prop).__name__] = getattr(prop, 'wtforms_convert')
    super(AdminConverter, self).__init__(*args, **kwargs)


def create(model, only=None, exclude=None, base_class=WTForm, converter=None,
           pre_init=None, post_init=None, pre_save=None, post_save=None,
           field_validators=None):
  '''Factory for admin forms.

  Input:
    * model - class to be used for wtforms creation
    * only - tuple of field names that should be exposed in the form
    * exclude - marked separately as read-only when editing,
                but still editable for new instances

  All the following receive the form and the object as parameters:
  (Note that the object may be None for new model instances)
    * pre_init - hook called before initializing the form, for a chance to
                 modify the instance before editing
    * post_init - hook called immediately after initializing the form, can be useful
                  to modify the form before display
    * pre_save, post_save - hooks called before/after saving an item

  All the following receive the form and the field as parameters:
    * field_validators - a dict of field -> callback function for validating
                         individual properties
  '''
  converter = converter or AdminConverter(model)
  form = model_form(
    model=model, base_class=base_class, only=only, exclude=exclude, converter=converter)
  form.model = model
  form.pre_init = pre_init
  form.post_init = post_init
  form.pre_save = pre_save
  form.post_save = post_save
  if field_validators:
    for field_name, validators in field_validators.items():
      if not isinstance(validators, (list, tuple)):
        field_validators[field_name] = [validators]
  form.field_validators = field_validators
  form.converter = converter
  return form
