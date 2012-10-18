from functools import partial

from . import wtforms
from wtforms import widgets as w


class DateTextInput(w.TextInput):
  '''Custom datetime text widget with an added class for easy JavaScript targeting.'''
  def __call__(self, *args, **kwargs):
    kwargs.setdefault('class', 'admin-date')
    return super(DateTextInput, self).__call__(*args, **kwargs)


class DateTimeTextInput(w.TextInput):
  '''Custom date text widget with an added class for easy JavaScript targeting.'''
  def __call__(self, *args, **kwargs):
    kwargs.setdefault('class', 'admin-datetime')
    return super(DateTimeTextInput, self).__call__(*args, **kwargs)


class AjaxKeyWidget(object):
  '''A ListProperty-compatible widget to easily manage Key entries.

  Pass object_classes to suggest what types of objects are allowed for lookup.
  The widget also includes any classes that are currently referenced
  in the list property.

  For lists of db.Key, this widget offers AJAX pagination of the above mentioned
  classes and allows for easy add/delete of each instance.

  '''

  def __init__(self, multiple=True):
    self.multiple = multiple

  def __call__(self, field, **kwargs):
    flat_attrs = w.core.html_params(name=field.name, **kwargs)

    # Convert the value into keys, objects and object classes
    field.process_formdata(field.data)

    from .handlers import AdminHandler
    handler = AdminHandler()

    from webapp2_extras import jinja2

    return jinja2.get_jinja2().render_template(
      'widgets/ajax_list_property.html',
      multiple=self.multiple,
      required=field.required,
      flat_attrs=flat_attrs,
      objects=field.objects,
      object_classes=field.object_classes,
      get_item_edit_url=partial(self._get_item_edit_url, handler=handler),
      get_reference_key=self._get_reference_key,
      name=field.name,
      paged_selector=partial(self._paged_selector, handler=handler),
    )

  @staticmethod
  def _get_reference_key(obj):
    return obj.admin_reference_key() if hasattr(obj, 'admin_reference_key') else obj.key()

  @staticmethod
  def _get_item_edit_url(model_instance, handler):
    return handler.uri_for('appengine_admin.edit', model_name=model_instance.__class__.__name__, key=model_instance.key())

  @staticmethod
  def _paged_selector(paged_cls, handler):
    from . import admin_settings, model_register
    from .utils import Http404, import_path, Paginator
    base_url = handler.uri_for('appengine_admin.list', model_name=paged_cls.__name__)
    try:
      model_admin = model_register.get_model_admin(paged_cls.__name__)
      paginator = Paginator(model_admin).get_page({}, base_url=base_url)
    except Http404:
      GenericPaginator = import_path(admin_settings.PAGINATOR_PATH)
      paginator = GenericPaginator(
        paged_cls,
        per_page=admin_settings.ADMIN_ITEMS_PER_PAGE
      ).get_page({}, base_url=base_url)
    return paginator
