import logging
import copy

from django.utils.encoding import smart_unicode
from google.appengine.api import datastore_errors
from google.appengine.ext import db

from . import admin_forms
from . import utils
from .utils import Http404


class PropertyWrapper(object):
    def __init__(self, cls, property_or_callback):
        self.cls = cls
        self.property_or_callback = property_or_callback
        if isinstance(property_or_callback, basestring):
          self.prop = getattr(cls, property_or_callback)
          self.name = property_or_callback
        elif hasattr(property_or_callback, '__call__'):
          self.prop = property_or_callback
          self.name = getattr(property_or_callback, '__name__', None) or property_or_callback.__class__.__name__
        self.verbose_name = getattr(self.prop, 'verbose_name', None) or self.name
        self.typeName = self.prop.__class__.__name__

    def getter(self, item):
        if isinstance(self.prop, db.Property):
            return getattr(item, self.name)
        return self.prop(item)

    def __deepcopy__(self, memo):
        return PropertyWrapper(self.cls, self.property_or_callback)

    def __str__(self):
        return "PropertyWrapper (name: %s; type: %s)" % (self.name, self.typeName)


class ModelAdmin(object):
    """Use this class as base for your model registration to admin site.
        Available settings:
        model - db.model derived class that describes your data model
        expect_duplicates - for pagination
        listFields - list of field names that should be shown in list view
        editFields - list of field names that that should be used as editable fields in admin interface
        readonlyFields - list of field names that should be used as read-only fields in admin interface
        listGql - GQL statement for record ordering/filtering/whatever_else in list view
    """
    model = None
    expect_duplicates = False
    listFields = ()
    editFields = ()
    readonlyFields = ()
    listGql = ''
    AdminForm = None

    def __init__(self):
        super(ModelAdmin, self).__init__()
        # Cache model name as string
        self.modelName = str(self.model.kind())
        self._listProperties = []
        self._editProperties = []
        self._readonlyProperties = []
        # extract properties from model by propery names
        self._extractProperties(self.listFields, self._listProperties)
        self._extractProperties(self.editFields, self._editProperties)
        self._extractProperties(self.readonlyFields, self._readonlyProperties)
        if self.AdminForm is None:
            self.AdminForm = admin_forms.createAdminForm(
                formModel=self.model,
                editFields=self.editFields,
                editProps=self._editProperties,
                readonlyFields=self.readonlyFields
            )

    def _extractProperties(self, fieldNames, storage):
        for propertyName in fieldNames:
            storage.append(PropertyWrapper(self.model, propertyName))

    def _attachListFields(self, item):
        """Attaches property instances for list fields to given data entry.
            This is used in Admin class view methods.
        """
        item.listProperties = copy.deepcopy(self._listProperties[:])
        for prop in item.listProperties:
            try:
                prop.value = prop.getter(item)
                if prop.typeName == 'BlobProperty':
                    prop.meta = utils.getBlobProperties(item, prop.name)
                    if prop.value:
                        prop.value = True  # release the memory
                if prop.typeName == 'ManyToManyProperty':
                    # Show pretty list of referenced items.
                    # Show 'None' in place of missing items
                    new_value_list = []
                    for key in prop.value:
                        new_value_list.append(smart_unicode(db.get(key)))
                    prop.value = ', '.join(new_value_list)
            except datastore_errors.Error, exc:
                # Error is raised if referenced property is deleted
                # Catch the exception and set value to none
                logging.warning('Error catched in ModelAdmin._attachListFields: %s' % exc)
                prop.value = None
            # convert the value to unicode for displaying in list view
            if hasattr(prop.value, '__call__'):
                # support for methods
                prop.value = prop.value()
            prop.value = smart_unicode(prop.value)
        return item


# holds model_name -> ModelAdmin_instance mapping.
_modelRegister = {}


def register(*args):
    """Registers ModelAdmin instance for corresponding model.
        Only one ModelAdmin instance per model can be active.
        In case if more ModelAdmin instances with same model are registered
        last registered instance will be the active one.
    """
    for modelAdminClass in args:
        modelAdminInstance = modelAdminClass()
        _modelRegister[modelAdminInstance.modelName] = modelAdminInstance
        logging.info("Registering AdminModel '%s' for model '%s'" % (modelAdminClass.__name__, modelAdminInstance.modelName))


def getModelAdmin(modelName):
    """Get ModelAdmin instance for particular model by model name (string).
        Raises Http404 exception if not found.
        This function is used internally by appengine_admin
    """
    try:
        return _modelRegister[modelName]
    except KeyError:
        raise Http404()
