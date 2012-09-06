import copy
import logging
import pickle

from google.appengine.api import datastore_errors
from google.appengine.ext import db


def get_blob_properties(item, field_name):
    from . import admin_settings
    props = getattr(item, field_name + admin_settings.BLOB_FIELD_META_SUFFIX, None)
    if props:
        return pickle.loads(props)
    else:
        return None


class Http404(Exception):
    code = 404


def import_path(path):
    class_path, _, class_name = path.rpartition('.')
    imported_module = __import__(class_path)
    _, _, module_name = class_path.rpartition('.')
    actual_module = getattr(imported_module, module_name)
    return getattr(actual_module, class_name)


class Paginator(object):
  def __init__(self, model_admin, items_per_page=None):
    from . import admin_settings
    # Set items_per_page here so the settings can be overriden anytime.
    items_per_page = items_per_page or admin_settings.ADMIN_ITEMS_PER_PAGE
    kwargs = {}
    if hasattr(model_admin, 'paginate_on'):
      kwargs['paginate_on'] = model_admin.paginate_on[0]
    GenericPaginator = import_path(admin_settings.PAGINATOR_PATH)
    paginator = GenericPaginator(
        model_admin.model, expect_duplicates=model_admin.expect_duplicates,
        per_page=items_per_page, **kwargs)
    self.get_page = paginator.get_page


def get_human_name(prop):
  return prop.capitalize().replace('_', ' ')


def get_dynamic_properties(item):
  if not item:
    return {}
  dynamic_properties = {}
  for prop in item.dynamic_properties():
    value = getattr(item, prop)
    if isinstance(value, basestring):
      dynamic_properties[prop] = db.TextProperty(verbose_name=get_human_name(prop))
      dynamic_properties[prop].value = value
      dynamic_properties[prop].form_field = dynamic_properties[prop].get_form_field().widget.render(prop, value)
  return dynamic_properties


def safe_get_by_key(model, key):
  '''Get record of particular model by key.

  Raise Http404 if not found or if the key is not in a correct format.

  '''
  try:
    item = model.get(key)
    return item
  except datastore_errors.BadKeyError:
    raise Http404('Bad key format.')
  raise Http404('Item not found.')


def get_readonly_properties_with_values(item, model_admin):
  readonly_properties = copy.deepcopy(model_admin._readonly_properties)
  for i, prop in enumerate(readonly_properties):
    itemValue = getattr(item, prop.name)
    prop.value = itemValue
    if prop.typeName == 'BlobProperty':
      logging.info("%s :: Binary content" % prop.name)
      prop.meta = get_blob_properties(item, prop.name)
      if prop.value:
        prop.value = True  # release the memory
    else:
      logging.info("%s :: %s" % (prop.name, prop.value))
  return readonly_properties
