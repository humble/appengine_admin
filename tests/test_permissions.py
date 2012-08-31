from google.appengine.api import users
import webapp2

from appengine_admin import admin_settings
from appengine_admin.authorized import check
from appengine_admin.tests import TestCase


class TestHandler(webapp2.RequestHandler):
  def __init__(self, *args, **Kwargs):
    class Request(object):
      uri = '/test'
      url = '/test'
    self.request = Request()

    class Response(object):
      status = 200

      def clear(*args, **kwargs):
        pass
    self.response = Response()

  def get(self, *args, **kwargs):
    return 'success!'

  def redirect(self, *args, **kwargs):
    pass


def fake_create_login_url(*args, **kwargs):
  return '/login/test'


def fake_get_current_user(user):
  return lambda *a, **kw: user


class DefaultCheckPermissionTests(TestCase):
  def extendedSetUp(self):
    self.old_create_login_url = users.create_login_url
    self.old_get_current_user = users.get_current_user
    self.old_is_current_user_admin = users.is_current_user_admin
    users.create_login_url = fake_create_login_url

  def extendedTearDown(self):
    users.create_login_url = self.old_create_login_url
    users.get_current_user = self.old_get_current_user
    users.is_current_user_admin = self.old_is_current_user_admin

  def test_default_check_not_logged_in(self):
    # Stubs
    users.get_current_user = fake_get_current_user(False)
    users.is_current_user_admin = lambda *a, **kw: False

    handler = TestHandler()
    checked_handler = check()
    check_wrapper = checked_handler(handler.get)
    result = check_wrapper(handler)
    self.assertIsNone(result)

  def test_default_check_admin(self):
    # Stubs
    users.get_current_user = fake_get_current_user(True)
    users.is_current_user_admin = lambda *a, **kw: True

    handler = TestHandler()
    checked_handler = check()
    check_wrapper = checked_handler(handler.get)
    result = check_wrapper(handler)
    self.assertEquals('success!', result)


def custom_check_with_arg(self, handler_method, check_args=[], check_kwargs={},
                          args=[], **kwargs):
  assert isinstance(self, TestHandler)
  if args[0] == 'first_arg' and kwargs.get('kwarg') == 'first_kwarg':
    return handler_method(self, *args, **kwargs)
  return 'fail'


class CustomCheckPermissionTests(TestCase):
  def extendedSetUp(self):
    self.old_callback = getattr(admin_settings, 'ACCESS_CALLBACK', None)

  def extendedTearDown(self):
    if self.old_callback:
      admin_settings.ACCESS_CALLBACK = self.old_callback
    else:
      del admin_settings.ACCESS_CALLBACK

  def test_custom_check_allowed_for_specific_arg(self):
    admin_settings.ACCESS_CALLBACK = custom_check_with_arg

    handler = TestHandler()
    checked_handler = check()
    check_wrapper = checked_handler(handler.get)
    result = check_wrapper(handler, 'first_arg', kwarg='first_kwarg')
    self.assertEquals('success!', result)

  def test_custom_check_disallowed_for_wrong_arg(self):
    admin_settings.ACCESS_CALLBACK = custom_check_with_arg

    handler = TestHandler()
    checked_handler = check()
    check_wrapper = checked_handler(handler.get)
    result = check_wrapper(handler, 'first_arg', kwarg='first_kwarg_wrong')
    self.assertEquals('fail', result)
