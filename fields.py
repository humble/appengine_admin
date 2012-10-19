from google.appengine.ext import db

from . import widgets, wtforms
from wtforms import fields as f


class DateTimeField(f.DateTimeField):
  '''Custom DateTimeField that use the appengine_admin DateTimeTextInput.'''
  widget = widgets.DateTimeTextInput()

  def __init__(self, *args, **kwargs):
    super(DateTimeField, self).__init__(*args, **kwargs)


class DateField(f.DateField):
  '''Custom DateField that use the appengine_admin DateTextInput.'''
  widget = widgets.DateTextInput()

  def __init__(self, *args, **kwargs):
    super(DateField, self).__init__(*args, **kwargs)


class AjaxKeyField(f.Field):
  '''A field with an AJAX paginator widget.

  Presents a UI for paginating with AJAX and easily adding/removing Key instances,
  either by str(key) values or with a UI list of objects (based on object_classes).

  Used for:
    * db.ListProprety (with multiple=True)
    * db.ReferenceProperty(db.Key) (with multiple=False)
  '''
  def __init__(self, label=None, validators=None, multiple=True,
               object_classes=None, required=False, **kwargs):
    super(AjaxKeyField, self).__init__(label, validators, **kwargs)

    self.multiple = multiple
    self.required = required
    self.object_classes = {kls.__name__: kls for kls in object_classes or []}
    self.widget = widgets.AjaxKeyWidget(multiple=multiple)

  def process_formdata(self, valuelist):
    self.objects = []
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

    self.data = keys
