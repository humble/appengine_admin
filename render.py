import os

import jinja2

from . import admin_settings


templates_path = [
  admin_settings.ADMIN_TEMPLATE_DIR,
]
config = {
  'autoescape': True,  # better safe than sorry
  'cache_size': -1,  # never clear the cache
  'extensions': ['jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
  # make None values output as empty strings
  'finalize': lambda x: x if x is not None else '',
  'loader': jinja2.FileSystemLoader(templates_path),
}

# Don't check for template updates in production
if os.environ['SERVER_SOFTWARE'].startswith('Devel'):
  config['auto_reload'] = True
else:
  config['auto_reload'] = False

env = jinja2.Environment(**config)


def template(path, template_kwargs={}):
  return env.get_template(path).render(template_kwargs)
