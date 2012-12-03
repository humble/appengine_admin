from datetime import datetime

from google.appengine.ext import db

from . import widgets, wtforms
from wtforms import fields as f


class DateTimeField(f.DateTimeField):
  '''Custom DateTimeField that use the appengine_admin DateTimeTextInput.'''
  widget = widgets.DateTimeTextInput()

  def __init__(self, *args, **kwargs):
    kwargs['format'] = '%Y-%m-%d %H:%M:%S %Z'  # output format
    super(DateTimeField, self).__init__(*args, **kwargs)
    self.input_format = '%Y-%m-%d %H:%M:%S'

  def process_data(self, value):
    if not isinstance(value, datetime):
      # Non-datetime values are left alone
      super(DateTimeField, self).process_data(value)
    else:
      # Already localized values are not localized
      from . import admin_settings, utils
      try:
        pytz = utils.import_pytz()
      except ImportError:  # Fall back to default behavior if no pytz available
        return super(DateTimeField, self).process_data(value)
      zone = pytz.timezone(admin_settings.TIMEZONE)
      if not value.tzinfo:
        value = pytz.utc.localize(value)
      self.data = value.astimezone(zone)

  def _value(self):
    try:
      from . import utils
      utils.import_pytz()
    except ImportError:  # Fall back to default behavior if no pytz available
      return super(DateTimeField, self).value()
    if self.raw_data:
      return ' '.join(self.raw_data)
    else:
      data = self.data and self.data.strftime(self.format) or ''
      if self.data.tzinfo:
        return data.replace(self.data.tzinfo._tzname, self.data.tzinfo.zone)
      return data

  def process_formdata(self, valuelist):
    if valuelist:
      date_str = ' '.join(valuelist).strip()
      from . import utils
      pytz = utils.import_pytz()
      date_without_tz, _, zone_name = date_str.rpartition(' ')
      try:
        zone = pytz.timezone(zone_name)
      except pytz.UnknownTimeZoneError:
        raise ValueError(self.gettext('Not a valid timezone value'))
      try:
        self.data = zone.localize(datetime.strptime(date_without_tz, self.input_format))
      except ValueError:
        self.data = None
        raise ValueError(self.gettext('Not a valid datetime value'))

class DateField(f.DateField):
  '''Custom DateField that use the appengine_admin DateTextInput.'''
  widget = widgets.DateTextInput()

  def __init__(self, *args, **kwargs):
    super(DateField, self).__init__(*args, **kwargs)


class DecimalField(f.DecimalField):
  def __init__(self, places=None, **kwargs):
    super(DecimalField, self).__init__(places=places, **kwargs)

  def process_formdata(self, valuelist):
    if valuelist and valuelist[0] not in ('', None):
      super(DecimalField, self).process_formdata(valuelist)


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
