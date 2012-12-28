import logging
import os

from google.appengine.api import datastore_errors
from google.appengine.ext import db


class Http404(Exception):
    code = 404


def import_path(path):
    class_path, _, class_name = path.rpartition('.')
    imported_module = __import__(class_path)
    _, _, module_name = class_path.rpartition('.')
    actual_module = getattr(imported_module, module_name)
    return getattr(actual_module, class_name)


def import_pytz():  # XXX: import pytz in a less hacky way
    from global_modules.pytz.gae import pytz
    return pytz


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
  from . import admin_settings
  if admin_settings.FEATURE_PICKLE_PROPERTY_PATH:
    import pickle
    PickleProperty = import_path(admin_settings.FEATURE_PICKLE_PROPERTY_PATH)
  for prop in item.dynamic_properties():
    value = getattr(item, prop)
    if isinstance(value, basestring):
      if admin_settings.FEATURE_PICKLE_PROPERTY_PATH:
        # Check if it might be a PickleProperty.
        try:
          setattr(item, prop, pickle.loads(value))
          dynamic_properties[prop] = PickleProperty(verbose_name=get_human_name(prop))
        except Exception:
          dynamic_properties[prop] = db.TextProperty(verbose_name=get_human_name(prop))
      else:
        dynamic_properties[prop] = db.TextProperty(verbose_name=get_human_name(prop))
      dynamic_properties[prop].value = value
      dynamic_properties[prop].name = prop
    # TODO: implement properties for other data types
  return dynamic_properties


def safe_get_by_key(model, key):
  '''Get record of particular model by key.

  Raise Http404 if not found or if the key is not in a correct format.

  '''
  try:
    item = model.get(key)
    if item:
      return item
  except datastore_errors.BadKeyError:
    raise Http404('Bad key format.')
  except db.KindError:
    raise Http404('Bad kind for key.')
  raise Http404('Item not found.')


def is_production():
  '''Determine if we are running in a production environment.'''
  if os.environ['SERVER_SOFTWARE'].startswith('Devel'):
    return False
  return True


def notify_if_configured(reason, requesthandler, **kwargs):
  logging.error(u'Error occured (reason %s): %s' % (reason, kwargs))
  from . import admin_settings
  notify_func = admin_settings.NOTIFY_CALLBACK
  if notify_func:
    notify_func(reason=reason, requesthandler=requesthandler, **kwargs)
