from datetime import datetime

from webob.multidict import MultiDict

from google.appengine.ext import db

from appengine_admin import admin_forms
from appengine_admin.tests import TestCase


class SubProject(db.Model):
  name = db.StringProperty()


class Project(db.Model):
  string_p = db.StringProperty(required=True)
  string_p_def = db.StringProperty(default='def_string')
  none_string_p = db.StringProperty(default=None)
  boolean_p = db.BooleanProperty()
  boolean_p_def = db.BooleanProperty(default=True)
  datetime_p = db.DateTimeProperty()
  datetime_p_def = db.DateTimeProperty(default=datetime(2012, 11, 12, 13, 14))
  list_p = db.ListProperty(db.Key)
  list_p_obj_classes = db.ListProperty(db.Key)
  list_p_obj_classes.object_classes = [SubProject]
  text_p = db.TextProperty()

  # TODO: tests with special properties
  # PickleProperty
  # DerivedProperty
  # LowerCaseProperty
  # DecimalProperty


def put_cls(cls, **kwargs):
  instance = cls(**kwargs)
  instance.put()
  return instance


class FormSaveTests(TestCase):
  def extendedSetUp(self):
    self.subproject1 = put_cls(SubProject, name='subproject 1')
    self.subproject2 = put_cls(SubProject, name='subproject 2')
    self.project1 = put_cls(
      Project, string_p='project 1', boolean_p=True,
      list_p=[self.subproject1.key(), self.subproject2.key()],
      list_p_obj_classes=[self.subproject2.key()],
      text_p='''This
      is some text.
      On multiple lines.'''
    )

  def extendedTearDown(self):
    pass

  def test_should_save_default_values_and_omitted_values_accordingly(self):
    formdata = MultiDict([
      ('string_p', 'project 1'),
      ('none_string_p', ''),
      ('boolean_p', 'y'),  # front-end-formatting
      # 'boolean_p_def' value should be changed to False, since it is not submitted
      ('datetime_p', '2012-12-13 23:00:00'),  # front-end formatting
      ('datetime_p_def', '2012-11-12 13:14:00'),
      ('list_p', str(self.subproject1.key())),
      ('list_p_obj_classes', str(self.subproject2.key())),
      ('list_p_obj_classes', str(self.subproject1.key())),
      ('text_p', u'This\r\n        is some text.\r\n        On multiple lines.'),
    ])
    form_cls = admin_forms.create(Project)
    form = form_cls(formdata=formdata, obj=self.project1)
    self.assertTrue(form.validate())

    unchanged_props = ('string_p', 'none_string_p', 'string_p_def', 'boolean_p', 'datetime_p', 'datetime_p_def', 'text_p')

    new_project = form.save()
    # Make sure unchanged properties are the same
    for prop in unchanged_props:
      self.assertEquals(getattr(self.project1, prop), getattr(new_project, prop))

    expected_values = {
      'boolean_p_def': False,
      'list_p': [self.subproject1.key()],
      'list_p_obj_classes': [self.subproject2.key(), self.subproject1.key()],
    }

    # Make sure changed properties are what they should be
    for prop in self.project1.properties().keys():
      if prop in unchanged_props:
        continue
      self.assertEquals(getattr(new_project, prop), expected_values[prop])

  def test_should_not_validate_if_required_value_is_missing(self):
    formdata = MultiDict([
      ('boolean_p', 'y'),  # front-end-formatting
      # 'boolean_p_def' value should be changed to False, since it is not submitted
      ('datetime_p', '2012-12-13 23:00:00'),  # front-end formatting
      ('datetime_p_def', '2012-11-12 13:14:00'),
      ('list_p', str(self.subproject1.key())),
      ('list_p_obj_classes', str(self.subproject2.key())),
      ('list_p_obj_classes', str(self.subproject1.key())),
      ('text_p', u'This\r\n        is some text.\r\n        On multiple lines.'),
    ])
    form_cls = admin_forms.create(Project)
    form = form_cls(formdata=formdata, obj=self.project1)
    self.assertFalse(form.validate())
    self.assertEquals({'string_p': [u'This field is required.']}, form.errors)
    self.assertRaises(db.BadValueError, form.save)
