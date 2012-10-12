from . import admin_forms, utils


# holds model_name -> ModelAdmin_instance mapping.
_model_register = {}


class PropertyMap(object):
  def __init__(self, name, prop_cls, value=None):
    self.name = name
    self.prop_cls = prop_cls
    self.value = value

  @property
  def verbose_name(self):
    return getattr(self.prop_cls, 'verbose_name', None) or utils.get_human_name(self.name)


class ModelAdmin(object):
  '''Extend ModelAdmin before you register your models to the admin.

    Available properties:
      * model - db.model derived class that describes your data model
      * expect_duplicates - for pagination
      * list_fields - list of field names that should be shown in list view
      * edit_fields - list of field names that that should be editable
      * readonly_fields - list of field names that should be read-only
      * pre_init, post_init, pre_save, post_save, field_validators
          - customize a model instance before init, before/after save, or with
            per-field processing/cleaning
          - see admin_forms.create for more details
  '''
  model = None
  expect_duplicates = False
  list_fields = ()
  edit_fields = ()
  readonly_fields = ()
  pre_init = None
  post_init = None
  pre_save = None
  post_save = None
  field_validators = None

  def __init__(self):
    super(ModelAdmin, self).__init__()
    # Cache model name as string
    self.model_name = str(self.model.kind())
    self.AdminForm = admin_forms.create(
      model=self.model,
      only=self.edit_fields,
      exclude=self.readonly_fields,
      pre_init=self.pre_init,
      post_init=self.post_init,
      pre_save=self.pre_save,
      post_save=self.post_save,
      field_validators=self.field_validators
    )

    self.AdminNewForm = admin_forms.create(
      model=self.model,
      pre_init=self.pre_init,
      post_init=self.post_init,
      pre_save=self.pre_save,
      post_save=self.post_save,
      field_validators=self.field_validators,
    )

  def list_model_iter(self, model):
    '''Create a generator to iterate through the list fields for an instance.

    Used to generate the rows when listing objects.
    '''
    for field_name in self.list_fields:
      if isinstance(field_name, basestring):
        yield getattr(model, field_name)
      elif callable(field_name):
        yield callable(model)

  def list_model_class_iter(self):
    '''Create a generator to iterate through the list fields for the model class.

    Used to generate the row heading when listing objects.
    '''
    model_class = self.model
    for field_name in self.list_fields:
      if isinstance(field_name, basestring):
        yield PropertyMap(field_name, getattr(model_class, field_name))
      elif callable(field_name):
        yield PropertyMap(field_name.__name__, field_name)

  def list_model_readonly_iter(self, model):
    '''Create a generator to iterate through the read-only fields for an instance.

    Used to generate the list of readonly properties when editing an item.
    '''
    for field_name in self.readonly_fields:
      yield PropertyMap(field_name, getattr(self.model, field_name), getattr(model, field_name))


def register(*args):
  '''Registers ModelAdmin instance for corresponding model.

  If more tha one ModelAdmin is registereed with the same model,
  only the last registered will be active.
  '''
  for model_admin_class in args:
    model_admin_instance = model_admin_class()
    _model_register[model_admin_instance.model_name] = model_admin_instance


def get_model_admin(model_name):
  '''Get ModelAdmin instance for particular model by model name (string).

  Raises utils.Http404 exception if not found.
  This function is used internally by appengine_admin
  '''
  try:
    return _model_register[model_name]
  except KeyError:
    raise utils.Http404()
