import copy
import datetime
from functools import partial
import logging
import pickle

from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from django import forms
from django.forms.util import ValidationError
from django.utils.translation import gettext as _

from . import admin_settings, admin_widgets, db_extensions, utils

MAX_BLOB_SIZE = admin_settings.MAX_BLOB_SIZE
BLOB_FIELD_META_SUFFIX = admin_settings.BLOB_FIELD_META_SUFFIX


class AdminModelForm(djangoforms.ModelForm):
    '''Custom admin handler, override appengine's django.ModelForm defaults.'''
    enctype = ''
    pre_init = None
    custom_clean = {}
    pre_save = None
    post_save = None

    def __init__(self, *args, **kwargs):
      instance = kwargs.get('instance', None)
      if instance and self.pre_init:
        instance = self.pre_init(instance)
      super(AdminModelForm, self).__init__(*args, **kwargs)

      for field_name, field in self.fields.items():
        # deliver meta info to FileInput widget for file download link display
        # do it only if file is uploaded :)
        if instance and isinstance(field.widget, admin_widgets.FileInput) and getattr(instance, field_name):
          meta = utils.get_blob_properties(instance, field_name)
          if meta:
            file_name = meta['File_Name']
          else:
            file_name = ''
          # these settings should be indivudual for every instance
          field = copy.copy(field)
          widget = copy.copy(field.widget)
          field.widget = widget
          self.fields[field_name] = field
          # set uploaded file meta data
          widget.show_download_url = True
          widget.model_name = instance.kind()
          widget.field_name = field_name
          widget.item_key = instance.key()
          widget.file_name = file_name

      # Special handling for dynamic properties
      self.dynamic_properties = utils.get_dynamic_properties(instance)

      for prop, func in self.custom_clean.items():
        if prop not in self._meta.model.properties().keys() + self.dynamic_properties.keys():
          continue
        setattr(self, 'clean_%s' % prop, partial(func, self))

    def clean(self, *args, **kwargs):
      c = super(AdminModelForm, self).clean(*args, **kwargs)

      # Special handling for dynamic properties
      if self.dynamic_properties:
        for prop, prop_cls in self.dynamic_properties.items():
          if not isinstance(prop_cls, db.TextProperty):
            continue
          data = self.data.getall(prop)
          if len(data) == 1:
            data = data[0]
          try:
            prop_cls.validate(data)
          except db.BadValueError as e:
            raise ValidationError(e.message)
          c[prop] = data

      return c

    def save(self, *args, **kwargs):
      '''Override to add custom admin behavior.

        * Uploaded file meta info for BlobProperty fields
        * Dynamic properties saving

      '''
      commit = kwargs.pop('commit', True)
      kwargs['commit'] = False
      item = super(AdminModelForm, self).save(*args, **kwargs)

      # Special handling for BlobProperty
      for field_name, field in self.fields.items():
        if isinstance(field, FileField) and field.file_name is not None:
          meta_field_name = field_name + BLOB_FIELD_META_SUFFIX
          if getattr(self.Meta.model, meta_field_name, None):
            meta_data = {
                'Content_Type': field.file_type,
                'File_Name': field.file_name,
                'File_Size': field.file_size,
            }
            logging.info("Caching meta data for BlobProperty: %r" % meta_data)
            setattr(item, meta_field_name, pickle.dumps(meta_data))
          else:
            logging.info(
              'Cache field "%(meta_field_name)s" for blob property "%(field_name)s" not found. Add field "%(meta_field_name)s" to model "%(model_name)s" if you want to store meta info about the uploaded file',
              {'meta_field_name': meta_field_name, 'field_name': field_name, 'model_name': self.Meta.model.kind()})

      # Special handling for dynamic properties
      if self.dynamic_properties:
        for prop, prop_cls in self.dynamic_properties.items():
          if not isinstance(prop_cls, db.TextProperty):
            continue
          if prop in self.cleaned_data:
            setattr(item, prop, self.cleaned_data[prop])

      if self.pre_save:  # hook before saving
        item = self.pre_save(item)
      # Save the item in Datastore if not told otherwise.
      if commit:
        item_or_result = item.put()
        if isinstance(item_or_result, item.__class__):
          item = item_or_result
        elif isinstance(item_or_result, db.Key):
          item = db.get(item_or_result)
      if self.post_save:  # hook after saving
        return self.post_save(item)
      return item


def create(form_model, edit_fields, readonly_fields, pre_init, custom_clean, pre_save, post_save):
    '''Factory for admin forms.

    Input:
      * form_model - class to be used for ModelForm creation
      * edit_fields - tuple of field names that should be exposed in the form
      * readonly_fields - marked separately as read-only when editing,
                          but still editable for new instances
      * pre_init - hook called before initializing the form, for a chance to
                   modify the instance before editing
      * custom_clean - a dict of field -> callback function for validating
                       individual properties
      * pre_save, post_save - hooks called before/after saving an item
    '''
    class AdminForm(AdminModelForm):
      class Meta:
        model = form_model
        fields = edit_fields
        exclude = readonly_fields

    AdminForm.pre_init = pre_init
    AdminForm.custom_clean = custom_clean
    AdminForm.pre_save = pre_save
    AdminForm.post_save = post_save

    # Adjust widgets by widget type
    for field_name, field in AdminForm.base_fields.items():
      if isinstance(field, djangoforms.ModelChoiceField):
        logging.info("  Adjusting field: %s; widget: %s" % (field_name, field.widget.__class__))
        # Use custom widget with link "Add new" near dropdown box
        field.widget = admin_widgets.ReferenceSelect(
          attrs=field.widget.attrs,
          reference_kind=getattr(form_model, field_name).reference_class.kind())
        # Choices must be set after creating the widget because in our case choices
        # is not a list but a wrapeper around query that always fetches fresh data from datastore
        field.widget.choices = field.choices
        if getattr(field.widget, 'needs_multipart_form', False):
          AdminForm.enctype = 'multipart/form-data'

    return AdminForm


class FileField(forms.fields.Field):
    widget = admin_widgets.FileInput
    error_messages = {
        'invalid': u"No file was submitted. Check the encoding type on the form.",
        'missing': u"No file was submitted.",
        'empty': u"The submitted file is empty.",
        'max_size': u"File size too big (%s bytes). Max size: %s bytes",
    }

    def __init__(self, *args, **kwargs):
        super(FileField, self).__init__(*args, **kwargs)
        self.file_name = None
        self.file_size = None
        self.file_type = None
        self.__args = args
        self.__kwargs = kwargs

    def __copy__(self):
        return FileField(*self.__args, **self.__kwargs)

    def clean(self, data, initial=None):
        super(FileField, self).clean(initial or data)

        if not self.required and data in forms.fields.EMPTY_VALUES:
            return None
        elif not data.value and initial:
            return initial

        # UploadedFile objects should have name and size attributes.
        try:
            self.file_name = data.filename
            self.file_size = len(data.value)
            self.file_type = data.type
            file_content = data.value
        except AttributeError:
            raise ValidationError(self.error_messages['invalid'])

        if not self.file_name:
            raise ValidationError(self.error_messages['invalid'])
        if not self.file_size:
            raise ValidationError(self.error_messages['empty'])
        if self.file_size > MAX_BLOB_SIZE:
            raise ValidationError(self.error_messages['max_size'] % (self.file_size, MAX_BLOB_SIZE))

        return file_content
forms.fields.FileField = FileField
forms.FileField = FileField


def _wrapped_get_value_for_form(self, instance):
    """Handle missing ReferenceProperty values.

    djangoforms.ReferenceProperty.get_value_for_form() does not catch the error
    that occurs when a referenced item is deleted.
    """
    try:
        return _original_get_value_for_form(self, instance)
    except datastore_errors.ReferencePropertyResolveError:
        # If the ReferenceProperty is deleted, an exception is raised.
        # Catch it and return None.
        return  None

_original_get_value_for_form = djangoforms.ReferenceProperty.get_value_for_form
djangoforms.ReferenceProperty.get_value_for_form = _wrapped_get_value_for_form


class ModelMultipleChoiceField(forms.MultipleChoiceField):
    default_error_messages = {
        'invalid_choice': _(u'Please select a valid choice. '
                            u'That is not one of the available choices.'),
    }

    def __init__(self, reference_class, query=None, choices=None,
                 required=True, widget=admin_widgets.SelectMultiple, label=None,
                 initial=None, help_text=None, *args, **kwargs):
        '''Constructor.

        Args:
          reference_class: required; the db.Model subclass used in the reference
          query: optional db.Query; default db.Query(reference_class)
          choices: optional explicit list of (value, label) pairs representing
            available choices; defaults to dynamically iterating over the
            query argument (or its default)
          required, widget, label, initial, help_text, *args, **kwargs:
            like for forms.Field.__init__(); widget defaults to forms.SelectMultiple
        '''
        assert issubclass(reference_class, db.Model)
        if query is None:
            query = db.Query(reference_class)
        assert isinstance(query, db.Query)
        self.reference_class = reference_class
        self._query = query
        self._choices = choices
        super(ModelMultipleChoiceField, self).__init__(
          choices, required, widget, label, initial,
          help_text, *args, **kwargs)
        self._update_widget_choices()

    def _update_widget_choices(self):
        """Helper to copy the choices to the widget."""
        self.widget.choices = self.choices

    def _get_query(self):
        """Getter for the query attribute."""
        return self._query

    def _set_query(self, query):
        """Setter for the query attribute.
        As a side effect, the widget's choices are updated.
        """
        self._query = query
        self._update_widget_choices()

    query = property(_get_query, _set_query)

    def _generate_choices(self):
        """Generator yielding (key, label) pairs from the query results.
        """
        for inst in self._query:
            yield (inst.key(), unicode(inst))

    def _get_choices(self):
        """Getter for the choices attribute.

        This is required to return an object that can be iterated over
        multiple times.
        """
        if self._choices is not None:
            return self._choices
        return djangoforms._WrapIter(self._generate_choices)

    def _set_choices(self, choices):
        """Setter for the choices attribute.
                As a side effect, the widget's choices are updated.
        """
        self._choices = choices
        self._update_widget_choices()

    choices = property(_get_choices, _set_choices)

    def clean(self, value):
        """Override Field.clean() to do reference-specific value cleaning.
        """
        value = super(ModelMultipleChoiceField, self).clean(value)
        new_value = []
        for item in value:
            if isinstance(item, basestring):
                item = db.Key(item)
            if isinstance(item, self.reference_class):
                item = item.key()
            if not isinstance(item, db.Key):
                raise db.BadValueError('Value must be a key or of type %s' %
                                       self.reference_class.__name__)
            new_value.append(item)
        return new_value


class MultipleChoiceField(forms.fields.MultipleChoiceField):
    def __init__(self, choices=(), required=True, widget=admin_widgets.SelectMultiple, label=None, initial=None, help_text=None, item_type=None):
        """Translates choices to Django style: [('key1', 'name1'), ('key2', 'name2')] instead of ['name1', 'name2']
        """
        choices = [(item, item) for item in choices]
        super(MultipleChoiceField, self).__init__(choices, required, widget, label, initial, help_text)


class ListPropertyField(forms.fields.MultipleChoiceField):
    def __init__(self, choices=(), required=True, widget=admin_widgets.AjaxListProperty, label=None, initial=None, help_text=None, item_type=None):
        """Translates choices to Django style: [('key1', 'name1'), ('key2', 'name2')] instead of ['name1', 'name2']
        """
        choices = [(item, item) for item in choices]
        super(ListPropertyField, self).__init__(choices, required, widget, label, initial, help_text)
        self.item_type = item_type

    def clean(self, value):
      if self.choices:
        return super(ListPropertyField, self).clean(value)

      if issubclass(self.item_type, db.Key):
        keys = []
        for str_key in value:
          if not str_key:
            continue
          keys.append(db.Key(str_key))
        return keys
      elif issubclass(self.item_type, basestring):
        return value

      # else:  # TODO: handle other data types
      return value


class ListProperty(db.ListProperty):
  __metaclass__ = djangoforms.monkey_patch

  def get_form_field(self, **kwargs):
    '''Return a Django form field appropriate for a ListProperty.'''
    defaults = {'form_class': ListPropertyField,
                'widget': admin_widgets.AjaxListProperty,
                'item_type': self.item_type}
    defaults.update(kwargs)
    return super(ListProperty, self).get_form_field(**defaults)

  def get_value_for_form(self, instance):
    value = super(ListProperty, self).get_value_for_form(instance)
    if not value:
      return None
    if isinstance(value, basestring):
      value = value.splitlines()
    return value


class StringListChoicesProperty(db_extensions.StringListChoicesProperty):
    __metaclass__ = djangoforms.monkey_patch

    def get_form_field(self, **kwargs):
        """Return a Django form field appropriate for a StringList property.

        This defaults to a Textarea widget with a blank initial value.
        """
        defaults = {'form_class': MultipleChoiceField,
                    'choices': self.choices,
                    'widget': admin_widgets.SelectMultiple}
        defaults.update(kwargs)
        return super(StringListChoicesProperty, self).get_form_field(**defaults)

    def get_value_for_form(self, instance):
        value = super(StringListChoicesProperty, self).get_value_for_form(instance)
        if not value:
            return None
        if isinstance(value, basestring):
            value = value.splitlines()
        return value


class DateTimeProperty(djangoforms.DateTimeProperty):
  __metaclass__ = djangoforms.monkey_patch

  def get_form_field(self, **kwargs):
    '''Return a Django form field appropriate for a date-time property.

    This defaults to a DateTimeField instance, except if auto_now or
    auto_now_add is set, in which case None is returned, as such
    'auto' fields should not be rendered as part of the form.
    '''
    defaults = {'widget': forms.DateTimeInput(attrs={'class': 'admin-datetime'})}
    defaults.update(kwargs)
    return super(DateTimeProperty, self).get_form_field(**defaults)

  def make_value_from_form(self, value):
    '''Override djangoforms' default value handling for DateTimeProperty.'''
    return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
