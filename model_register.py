import logging
import copy

from django.utils.encoding import smart_unicode
from google.appengine.api import datastore_errors
from google.appengine.ext import db

from . import admin_forms, utils
from .utils import Http404


class PropertyWrapper(object):
    def __init__(self, cls, property_or_callback):
        self.cls = cls
        self.property_or_callback = property_or_callback
        if isinstance(property_or_callback, basestring):
          self.prop = getattr(cls, property_or_callback)
          self.name = property_or_callback
        elif hasattr(property_or_callback, '__call__'):
          self.prop = property_or_callback
          self.name = getattr(property_or_callback, '__name__', None) or property_or_callback.__class__.__name__
        self.verbose_name = getattr(self.prop, 'verbose_name', None) or self.name
        if self.verbose_name.lower() == self.verbose_name:
          self.verbose_name = utils.get_human_name(self.verbose_name)
        self.typeName = self.prop.__class__.__name__

    def getter(self, item):
        if isinstance(self.prop, db.Property):
            return getattr(item, self.name)
        return self.prop(item)

    def __deepcopy__(self, memo):
        return PropertyWrapper(self.cls, self.property_or_callback)

    def __str__(self):
        return "PropertyWrapper (name: %s; type: %s)" % (self.name, self.typeName)


class ModelAdmin(object):
  '''Extend ModelAdmin before you register your models to the admin.

    Available properties:
      * model - db.model derived class that describes your data model
      * expect_duplicates - for pagination
      * list_fields - list of field names that should be shown in list view
      * edit_fields - list of field names that that should be editable
      * readonly_fields - list of field names that should be read-only
      * list_gql - GQL statement for ordering/filtering in list view
  '''
  model = None
  expect_duplicates = False
  list_fields = ()
  edit_fields = ()
  readonly_fields = ()
  list_gql = ''
  AdminForm = None
  AdminNewForm = None
  pre_init = None
  custom_clean = None
  pre_save = None
  post_save = None

  def __init__(self):
    super(ModelAdmin, self).__init__()
    # Cache model name as string
    self.model_name = str(self.model.kind())
    self._list_properties = []  # Store the list of fields that should be shown in list view.
    self._edit_properties = []
    self._readonly_properties = []
    # extract properties from model by propery names
    self._extractProperties(self.list_fields, self._list_properties)
    self._extractProperties(self.edit_fields, self._edit_properties)
    self._extractProperties(self.readonly_fields, self._readonly_properties)
    if self.AdminForm is None:
      self.AdminForm = admin_forms.create(
        form_model=self.model,
        edit_fields=self._edit_properties,
        readonly_fields=self.readonly_fields,
        pre_init=self.pre_init,
        custom_clean=self.custom_clean,
        pre_save=self.pre_save,
        post_save=self.post_save,
      )
      self.AdminNewForm = admin_forms.create(
        form_model=self.model,
        edit_fields=[],
        readonly_fields=[],
        pre_init=self.pre_init,
        custom_clean=self.custom_clean,
        pre_save=self.pre_save,
        post_save=self.post_save,
      )

  def _extractProperties(self, field_names, storage):
    for field_name in field_names:
      storage.append(PropertyWrapper(self.model, field_name))

  def _attachListFields(self, item):
    '''Attaches property instances for list fields to given data entry.

    This is used in Admin class view methods.
    '''
    # TODO: implement this in a cleaner way
    item._list_properties_copy = copy.deepcopy(self._list_properties[:])
    for prop in item._list_properties_copy:
      try:
        prop.value = prop.getter(item)
        if prop.typeName == 'BlobProperty':
          prop.meta = utils.get_blob_properties(item, prop.name)
          if prop.value:
            prop.value = True  # release the memory
        if prop.typeName == 'ManyToManyProperty':
          # Show pretty list of referenced items.
          # Show 'None' in place of missing items
          new_value_list = []
          for key in prop.value:
            new_value_list.append(smart_unicode(db.get(key)))
          prop.value = ', '.join(new_value_list)
      except datastore_errors.Error, exc:
        # Error is raised if referenced property is deleted
        # Catch the exception and set value to none
        logging.warning('Error catched in ModelAdmin._attachListFields: %s' % exc)
        prop.value = None
      # convert the value to unicode for displaying in list view
      if hasattr(prop.value, '__call__'):
        # support for methods
        prop.value = prop.value()
      prop.value = smart_unicode(prop.value)
    return item


# holds model_name -> ModelAdmin_instance mapping.
_model_register = {}


def register(*args):
  '''Registers ModelAdmin instance for corresponding model.

  If more tha one ModelAdmin is registereed with the same model,
  only the last registered will be active.
  '''
  for model_admin_class in args:
    model_admin_instance = model_admin_class()
    _model_register[model_admin_instance.model_name] = model_admin_instance
    logging.info("Registering AdminModel '%s' for model '%s'" % (model_admin_class.__name__, model_admin_instance.model_name))


def get_model_admin(model_name):
  '''Get ModelAdmin instance for particular model by model name (string).

  Raises Http404 exception if not found.
  This function is used internally by appengine_admin
  '''
  try:
    return _model_register[model_name]
  except KeyError:
    raise Http404()
