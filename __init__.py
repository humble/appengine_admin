from webapp2_extras.routes import RedirectRoute

from .model_register import register, ModelAdmin


def get_application_routes(handler_cls=None):
  from . import admin_settings
  if not handler_cls:
    from .handlers import AdminHandler
    handler_cls = AdminHandler
  if handler_cls.__name__ in admin_settings._application_routes:
    return admin_settings._application_routes[handler_cls.__name__]

  application_routes = (
    ('appengine_admin.index', 'GET', r'/', handler_cls, 'index'),
    ('appengine_admin.list', 'GET', r'/<model_name>/list/', handler_cls, 'list'),
    ('appengine_admin.new', None, r'/<model_name>/new/', handler_cls, 'new'),
    ('appengine_admin.edit', None, r'/<model_name>/edit/<key>/', handler_cls, 'edit'),
    ('appengine_admin.clone', 'GET', r'/<model_name>/clone/<key>/', handler_cls, 'clone'),
    ('appengine_admin.delete', 'POST', r'/<model_name>/delete/<key>/', handler_cls, 'delete'),
    ('appengine_admin.blob', 'GET', r'/<model_name>/blob/<field_name>/<key>/', handler_cls, 'blob'),
  )

  admin_settings._application_routes[handler_cls.__name__] = []
  for name, methods, pattern, handler_cls, handler_method in application_routes:
    if isinstance(methods, basestring):
      methods = [methods]

    # Prefix with the base URL.
    pattern = admin_settings.ADMIN_BASE_URL + pattern

    # Create the route
    route = RedirectRoute(name=name, template=pattern, methods=methods,
                          handler=handler_cls, handler_method=handler_method,
                          strict_slash=True)

    admin_settings._application_routes[handler_cls.__name__].append(route)

  # Read only!
  admin_settings._application_routes[handler_cls.__name__] = tuple(admin_settings._application_routes[handler_cls.__name__])
  return admin_settings._application_routes[handler_cls.__name__]


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
      'template_path': admin_settings.ADMIN_TEMPLATE_PATHS,
    }
  }
  return admin_settings._webapp2_config
