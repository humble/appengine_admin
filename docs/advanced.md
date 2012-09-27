# Not organized things you can do

* Specify your own AdminHandler to e.g. render your own error pages and use your own sessions.

  ```python
  class YourBaseHandler(webapp2.RequestHandler):
    def self.error(self, code):
      # render your own error pages here

  from appengine_admin import handlers
  class YourAdminHandler(YourBaseHandler, handlers.AdmimHandler):
    pass

  app = WSGIApplication(
    routes=appengine_admin.get_application_routes(YourAdminHandler),
    config=app_config,
    debug=DEBUG)
  ```

* Specify object_classes for AjaxListProperty widget, useful when creating new objects:

  ```python
  class Item(db.Expando):
    pass

  class YourModel(db.Expando):
    items = db.ListProperty(db.Key)
    items.object_classes = [Item]
  ```

* Add readonly=True to any wtforms.Field subclasses to skip them in the validation/save steps

* Implement Property.wtforms_convert to convert your appengine db.Property to a field for wtforms:

  ```
  class YourProperty(db.Property):
    @staticmethod
    def wtforms_convert(model, prop, kwargs):
      """Return a wtforms field appropriate for your property."""
      from appengine_admin import wtforms
      from wtforms import fields, widgets

      def your_widget(field, **kwargs):
        value = field._value()
        return widgets.core.HTMLString(u'<div %s>%s</div> (your custom widget)'
          % (widgets.core.html_params(name=field.name, **kwargs), value))

      class YourField(fields.TextField):
        readonly = True  # This makes sure it's not validated or saved to form.data
        widget = your_widget
  ```

* Go through settings and explain each
