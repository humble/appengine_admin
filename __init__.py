from webapp2_extras.routes import RedirectRoute

from .handlers import Admin
from .model_register import register, ModelAdmin


def get_application_routes():
  from . import admin_settings
  if admin_settings._application_routes:
    return admin_settings._application_routes

  application_routes = (
    ('appengine_admin.index', 'GET', r'/', Admin, 'index'),
    ('appengine_admin.list', 'GET', r'/<model_name>/list/', Admin, 'list'),
    ('appengine_admin.new', None, r'/<model_name>/new/', Admin, 'new'),
    ('appengine_admin.edit', None, r'/<model_name>/edit/<key>/', Admin, 'edit'),
    ('appengine_admin.delete', 'POST', r'/<model_name>/delete/<key>/', Admin, 'delete'),
    ('appengine_admin.blob', 'GET', r'/<model_name>/blob/<field_name>/<key>/', Admin, 'blob'),
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
