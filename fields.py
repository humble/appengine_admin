from google.appengine.ext import db

from . import widgets, wtforms
from wtforms import fields as f


class DateTimeField(f.DateTimeField):
  widget = widgets.DateTimeTextInput()

  def __init__(self, *args, **kwargs):
    super(DateTimeField, self).__init__(*args, **kwargs)


class DateField(f.DateField):
  widget = widgets.DateTextInput()

  def __init__(self, *args, **kwargs):
    super(DateField, self).__init__(*args, **kwargs)


class AjaxKeyField(f.Field):
  def __init__(self, label=None, validators=None, multiple=True,
               object_classes=None, required=False, **kwargs):
    super(AjaxKeyField, self).__init__(label, validators, **kwargs)

    self.multiple = multiple
    self.required = required
    self._object_classes = {kls.__name__: kls for kls in object_classes or []}
    self.widget = widgets.AjaxKeyWidget(multiple=multiple)

  def process_formdata(self, valuelist):
    self.objects = []
    self.object_classes = {}
    self.object_classes.update(self._object_classes)
    if not self.multiple:
      if not valuelist:
        self.data = None
        return
      if isinstance(valuelist, list):
        value = valuelist[0]
      else:
        value = valuelist
      if isinstance(value, basestring):
        value = db.get(value)
      self.data = value
      self.objects.append((value.key(), value))
      return

    # TODO: consider self.multiple
    if not valuelist:
      self.data = []
      return
    if not isinstance(valuelist, list):
      self.data = []
      return

    keys = []

    for key_str in valuelist:
      if not key_str:
        continue
      # Turn string keys into Key objects
      if isinstance(key_str, db.Key):
        key = key_str
      else:
        key = db.Key(key_str)
      keys.append(key)
      obj = db.get(key)
      self.objects.append((key, obj))
      self.object_classes[obj.__class__.__name__] = obj.__class__

    self.data = keys
