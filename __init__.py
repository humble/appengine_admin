from webapp2_extras.routes import RedirectRoute

from .handlers import AdminHandler
from .model_register import register, ModelAdmin


def get_application_routes():
  from . import admin_settings
  if admin_settings._application_routes:
    return admin_settings._application_routes

  application_routes = (
    ('appengine_admin.index', 'GET', r'/', AdminHandler, 'index'),
    ('appengine_admin.list', 'GET', r'/<model_name>/list/', AdminHandler, 'list'),
    ('appengine_admin.new', None, r'/<model_name>/new/', AdminHandler, 'new'),
    ('appengine_admin.edit', None, r'/<model_name>/edit/<key>/', AdminHandler, 'edit'),
    ('appengine_admin.delete', 'POST', r'/<model_name>/delete/<key>/', AdminHandler, 'delete'),
    ('appengine_admin.blob', 'GET', r'/<model_name>/blob/<field_name>/<key>/', AdminHandler, 'blob'),
  )

  admin_settings._application_routes = []
  for name, methods, pattern, handler_cls, handler_method in application_routes:
    if isinstance(methods, basestring):
      methods = [methods]

    # Prefix with the base URL.
    pattern = admin_settings.ADMIN_BASE_URL + pattern

    # Create the route
    route = RedirectRoute(name=name, template=pattern, methods=methods,
                          handler=handler_cls, handler_method=handler_method,
                          strict_slash=True)

    admin_settings._application_routes.append(route)

  # Read only!
  admin_settings._application_routes = tuple(admin_settings._application_routes)
  return admin_settings._application_routes


def get_webapp2_config():
  from . import admin_settings, utils
  if admin_settings._webapp2_config:
    return admin_settings._webapp2_config

  admin_settings._webapp2_config = {
    'webapp2_extras.jinja2': {
      'environment_args': {
        'autoescape': True,  # better safe than sorry
        # Don't check for template updates in production
        'auto_reload': not utils.is_production(),
        'cache_size': -1,  # never clear the cache
        'extensions': ['jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
        # make None values output as empty strings
        'finalize': lambda x: x if x is not None else '',
      },
      'globals': {
        'DEBUG': not utils.is_production(),
        'media_url': admin_settings.ADMIN_MEDIA_URL,
      },
      'template_path': admin_settings.ADMIN_TEMPLATE_PATH,
    }
  }
  return admin_settings._webapp2_config
