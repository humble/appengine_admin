import json
import sys
import traceback

import webapp2
from webapp2_extras import jinja2, sessions

from . import admin_settings, authorized, model_register, utils


CSRFHandler = utils.import_path(admin_settings.CSRF_HANDLER_PATH)


class BaseRequestHandler(CSRFHandler):
  def handle_exception(self, exception, debug_mode):
    if isinstance(exception, utils.Http404):
      self.error(exception.code)
      path = '%s.html' % exception.code
      self.render(path, {'errorpage': True})
      return
    utils.notify_if_configured(reason='handler_exception',
                               exception=exception, debug_mode=debug_mode,
                               traceback=traceback.format_exception(*sys.exc_info()),
                               session=self.session)
    self.render('500.html', {'errorpage': True})

  @webapp2.cached_property
  def jinja2_instance(self):
    '''Get a jinja2 renderer and cache it in the app registry.'''
    return jinja2.get_jinja2(app=self.app)

  def render(self, path, template_kwargs={}):
    template_kwargs.update({
      'uri_for': lambda route_name, *a, **kw: self.uri_for('appengine_admin.%s' % route_name, *a, **kw),
      'get_messages': self.get_messages,
      'csrf_token': self.get_csrf_token,
      'settings': {
        'TIMEZONE': admin_settings.TIMEZONE,
      }
    })
    if hasattr(self, 'models'):
      template_kwargs['models'] = self.models
    self.response.write(self.jinja2_instance.render_template(path, **template_kwargs))

  def redirect_admin(self, route_name, *args, **kwargs):
    self.redirect(self.uri_for('appengine_admin.%s' % route_name, *args, **kwargs))

  def json_response(self, data):
    '''Encode and add JSON data to the response.'''
    self.response.out.write(json.dumps(data))

  def dispatch(self):
    # Get a session store for this request.
    self.session_store = sessions.get_store(request=self.request)
    try:
      # Dispatch the request.
      webapp2.RequestHandler.dispatch(self)
    finally:
      # Save all sessions.
      self.session_store.save_sessions(self.response)

  @webapp2.cached_property
  def session(self):
    '''Returns a session using the default cookie key.'''
    return self.session_store.get_session()

  def add_message(self, message):
    self.session['messages'] = self.session.get('messages') or [] + [message]

  def get_messages(self):
    messages = self.session.get('messages') or []
    if messages:
      del self.session['messages']
    return messages


class AdminHandler(BaseRequestHandler):
  '''Use this class as the central handler in your app routing.

  Example:
  ===
  import appengine_admin

  app = WSGIApplication(
    routes=appengine_admin.get_application_routes(),
    config=app_config,
    debug=DEBUG)
  ===
  '''

  def __init__(self, *args, **kwargs):
    super(AdminHandler, self).__init__(*args, **kwargs)
    self.models = model_register._model_register.keys()
    self.models.sort()

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def index(self, template_kwargs=None):
    '''Admin start page.'''
    template_kwargs = template_kwargs or {}
    template_kwargs.update({
      'models': self.models,
    })
    self.render('index.html', template_kwargs)

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def list(self, model_name, template_kwargs=None):
    '''List entities for a model by name.'''
    model_admin = model_register.get_model_admin(model_name)
    paginator = utils.Paginator(model_admin=model_admin)
    # Get only those items that should be displayed in current page
    page = paginator.get_page(request=self.request)
    items = list(page)
    if self.request.get('ajax_mini_page'):
      json_items = [{
        'key': str(item.admin_reference_key() if hasattr(item, 'admin_reference_key') else item.key()),
        'name': unicode(item),
        'model_name': model_name,
        'edit_url': self.uri_for('appengine_admin.edit', model_name=model_name, key=item.key())
      } for item in items]
      if page.has_next():
        next_url = page.get_next_url()
      else:
        next_url = ''
      json_items.append({
        'next_url': next_url,
      })
      self.json_response(json_items)
      return
    template_kwargs = template_kwargs or {}
    template_kwargs.update({
      'model_name': model_admin.model_name,
      'list_class_fields': model_admin.list_model_class_iter(),
      'list_fields': model_admin.list_model_iter,
      'items': items,
      'page': page,
    })
    self.render('list.html', template_kwargs)

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def new(self, model_name, template_kwargs=None):
    '''Handle creating a new record for a particular model.'''
    model_admin = model_register.get_model_admin(model_name)
    if self.request.method == 'POST':
      item_form = model_admin.AdminNewForm(formdata=self.request.POST, handler=self)
      if item_form.validate():
        # Save the data, and redirect to the edit page
        item = item_form.save()
        self.add_message('%s %s created!' % (model_name, unicode(item)))
        self.redirect_admin('edit', model_name=model_admin.model_name, key=item.key())
        return
    else:
      item_form = model_admin.AdminNewForm(handler=self)

    template_kwargs = template_kwargs or {}
    template_kwargs.update({
      'item': None,
      'model_name': model_admin.model_name,
      'item_form': item_form,
    })
    self.render('edit.html', template_kwargs)

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def edit(self, model_name, key, template_kwargs=None):
    '''Edit an editing existing record for a particular model.
    Returns a tuple of (item, saved) where saved is True if the function has saved changes.
    Raises Http404 if record is not found.
    '''
    model_admin = model_register.get_model_admin(model_name)
    item = utils.safe_get_by_key(model_admin.model, key)
    if not item:
      raise utils.Http404()

    dynamic_properties = utils.get_dynamic_properties(item)
    for prop_name, prop_cls in dynamic_properties.items():
      setattr(model_admin.AdminForm, prop_name, model_admin.AdminForm.converter.convert(item.__class__, prop_cls, None))
    model_admin.AdminForm.dynamic_properties = dynamic_properties
    if self.request.method == 'POST':
      item_form = model_admin.AdminForm(formdata=self.request.POST, obj=item, handler=self)
      if item_form.validate():
        # Save the data, and redirect to the edit page
        item = item_form.save()
        self.add_message('%s %s updated.' % (model_name, unicode(item)))
        self.redirect_admin('edit', model_name=model_admin.model_name, key=item.key())
        return item, True
    else:
      item_form = model_admin.AdminForm(obj=item, handler=self)

    template_kwargs = template_kwargs or {}
    template_kwargs.update({
      'item': item,
      'model_name': model_admin.model_name,
      'item_form': item_form,
      'readonly_properties': model_admin.list_model_readonly_iter(item),
    })
    self.render('edit.html', template_kwargs)
    for prop_name, prop_cls in dynamic_properties.items():
      delattr(model_admin.AdminForm, prop_name)

    return item, False

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def delete(self, model_name, key):
    '''Delete a record for a particular model.

    Raises Http404 if the record not found.
    '''
    model_admin = model_register.get_model_admin(model_name)
    item = utils.safe_get_by_key(model_admin.model, key)
    if not item:
      raise utils.Http404()
    item.delete()
    if self.request.get('goto'):
      self.redirect(self.request.get('goto'))
    else:
      self.redirect_admin('list', model_name=model_admin.model_name)

  @BaseRequestHandler.csrf_token_required()
  @authorized.check()
  def blob(self, model_name, field_name, key):
    '''Returns blob field contents.'''
    model_admin = model_register.get_model_admin(model_name)
    item = utils.safe_get_by_key(model_admin.model, key)
    data = getattr(item, field_name, None)
    if data is None:
      raise utils.Http404()

    props = utils.get_blob_properties(item, field_name)
    if props:
      self.response.headers['Content-Type'] = props['Content_Type']
      self.response.headers['Content-Disposition'] = 'inline; filename=%s' % props['File_Name']
    else:
      self.response.headers['Content-Type'] = 'application/octet-stream'
    self.response.out.write(data)
