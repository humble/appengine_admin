import os
import pickle

import jinja2

from appengine_admin import admin_settings


def getBlobProperties(item, fieldName):
    props = getattr(item, fieldName + admin_settings.BLOB_FIELD_META_SUFFIX, None)
    if props:
        return pickle.loads(props)
    else:
        return None


class Http404(Exception):
    code = 404


def import_path(path):
    class_path, _, class_name = path.rpartition('.')
    imported_module = __import__(class_path)
    _, _, module_name = class_path.rpartition('.')
    actual_module = getattr(imported_module, module_name)
    return getattr(actual_module, class_name)


class Paginator(object):
    def __init__(self, modelAdmin, itemsPerPage=20):
        kwargs = {}
        if hasattr(modelAdmin, 'paginate_on'):
          kwargs['paginate_on'] = modelAdmin.paginate_on[0]
        from appengine_admin import admin_settings
        GenericPaginator = import_path(admin_settings.PAGINATOR_PATH)
        paginator = GenericPaginator(
            modelAdmin.model, expect_duplicates=modelAdmin.expect_duplicates,
            per_page=itemsPerPage, **kwargs)
        self.get_page = paginator.get_page


config = {
  'autoescape': True,  # better safe than sorry
  'cache_size': -1,  # never clear the cache
  'extensions': ['jinja2.ext.with_'],
  # make None values output as empty strings
  'finalize': lambda x: x if x is not None else '',
}

# Don't check for template updates in production
if os.environ['SERVER_SOFTWARE'].startswith('Devel'):
  config['auto_reload'] = True
else:
  config['auto_reload'] = False

templates_path = [
  os.path.join(os.path.dirname(__file__), 'templates'),
]
config['loader'] = jinja2.FileSystemLoader(templates_path)
env = jinja2.Environment(**config)


def render_template(path, template_kwargs={}):
  return env.get_template(path).render(template_kwargs)
