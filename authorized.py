def check(*check_args, **check_kwargs):
  def wrapper(handler_method):
    def check_wrapper(self, *args, **kwargs):
      from appengine_admin import admin_settings
      callback = getattr(admin_settings, 'ACCESS_CALLBACK', is_google_admin)
      return callback(self, handler_method=handler_method,
                      check_args=check_args, check_kwargs=check_kwargs, args=args, **kwargs)
    return check_wrapper
  return wrapper


def is_google_admin(self, handler_method=None, check_args=[], check_kwargs={},
                    args=[], **kwargs):
  '''Check if the user is authenticated as a google admin user.

  Overrideable by setting admin_settings.ACCESS_CALLBACK to your custom access
  function.

  '''
  from google.appengine.api import users
  user = users.get_current_user()
  role = check_args[0] if check_args else check_kwargs.get('role') or 'admin'

  if not user:
    self.redirect(users.create_login_url(self.request.uri))

  elif role == 'user' or (role == 'admin' and users.is_current_user_admin()):
    return handler_method(self, *args, **kwargs)

  self.error(403)  # User didn't meet role.
