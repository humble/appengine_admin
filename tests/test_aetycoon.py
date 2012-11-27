from decimal import Decimal

from unittest import SkipTest

from webob.multidict import MultiDict

from google.appengine.ext import db

from appengine_admin import admin_forms
from appengine_admin.tests import TestCase

try:
  from libraries import aetycoon
  try:
    from models.DecimalProperty import DecimalProperty
    has_decimal = True
    decimal_prop_cls = DecimalProperty
  except ImportError:
    has_decimal = False
    decimal_prop_cls = db.StringProperty

  class AESubProject(db.Model):
    name = db.StringProperty()

  class AEProject(db.Model):
    string_p = db.StringProperty()
    decimal_p = decimal_prop_cls(default='9.99')
    pickle_p = aetycoon.PickleProperty(default={})
    lowercase_p = aetycoon.LowerCaseProperty(string_p)

    @aetycoon.DerivedProperty(name='derived_p')
    def derived_p(self):
      return self.string_p[::-1] if self.string_p else 'enoN'
except ImportError:
  AESubProject = None
  AEProject = None


def put_cls(cls, **kwargs):
  instance = cls(**kwargs)
  instance.put()
  return instance


class FormSaveTests(TestCase):
  def extendedSetUp(self):
    if not AESubProject or not AEProject:
      raise SkipTest
    self.subproject1 = put_cls(AESubProject, name='subproject 1')
    self.subproject2 = put_cls(AESubProject, name='subproject 2')
    self.project1 = put_cls(
      AEProject, string_p='Project 1', decimal_p='1.99',
      pickle_p={'key_bool': True, 'key_int': 3, 'key_decimal': Decimal('2.02'), 'key_string': 'Some\nvalue'},
    )

  def extendedTearDown(self):
    pass

  def test_should_save_aetycoon_properties_properly(self):
    formdata = MultiDict([
      ('string_p', 'ProJect 1'),
      ('decimal_p', '1.99'),
      ('pickle_p', "{'key_bool': True, 'key_int': 3, 'key_decimal': Decimal('2.02'), 'key_string': 'Some\\nvalue'}"),
      ('lowercase_p', 'PROJECT ONE'),
      ('derived_p', 'fail'),
    ])
    form_cls = admin_forms.create(AEProject)
    form = form_cls(formdata=formdata, obj=self.project1)
    self.assertTrue(form.validate())

    unchanged_props = ('decimal_p', 'pickle_p', 'lowercase_p', 'derived_p')

    new_project = form.save()
    # Make sure unchanged properties are the same
    for prop in unchanged_props:
      self.assertEquals(getattr(self.project1, prop), getattr(new_project, prop))

    expected_values = {
      'string_p': 'ProJect 1',
    }

    # Make sure changed properties are what they should be
    for prop in self.project1.properties().keys():
      if prop in unchanged_props:
        continue
      self.assertEquals(getattr(new_project, prop), expected_values[prop])

  def test_should_not_validate_if_invalid_pickle_value(self):
    formdata = MultiDict([
      ('string_p', 'ProJect 1'),
      ('pickle_p', "{'inval\nid'}"),
    ])
    form_cls = admin_forms.create(AEProject)
    form = form_cls(formdata=formdata, obj=self.project1)
    self.assertFalse(form.validate())
    self.assertEquals({'pickle_p': ['Could not pickle set value.']}, form.errors)
    # TODO: self.assertRaises(db.BadValueError, form.save)
