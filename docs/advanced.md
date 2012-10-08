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

* Go through settings and explain each
