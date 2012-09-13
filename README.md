# App Engine Datastore Admin

`appengine_admin` is a flexible datastore admin for app engine. [MIT licensed](http://en.wikipedia.org/wiki/MIT_License).

* <a href="#start">Getting Started</a>
* <a href="#features">Features</a>
* <a href="#dependencies">Dependencies</a>
* <a href="#faq">FAQ</a>
* <a href="#todo">TODO</a>

## <span name="start">Getting Started</span>

1. Download this repository's source and copy the `appengine_admin/` folder at the root of your App Engine project directory.

2. Install [gae_paginator](https://github.com/humble/gae_paginator) and configure the setting for it like so:

   ```python
    import appengine_admin
    appengine_admin.admin_settings.PAGINATOR_PATH = 'path.to.paginator.Paginator'
    ```

3. Update your app.yaml to add the URLs:

    ```python
    - url: /appengine_admin_media
      static_dir: appengine_admin/media

    # Your custom handler goes here (see next step)
    - url: /admin/models.*
      script: handlers.admin.app
      secure: always
    ```

4. Use it like so, in your handlers (__full working example__):

    ```python
    import appengine_admin
    from webapp2 import RequestHandler, WSGIApplication

    # Declare your models.
    from google.appengine.ext import db

    class Artist(db.Expando):
      name = db.StringProperty()
      birthday = db.DateTimeProperty()

    class Album(db.Expando):
      name = db.StringProperty()
      release_year = db.StringProperty(default='2012')
      price = db.IntegerProperty()

    class Song(db.Expando):
      title = db.StringProperty()
      genre = db.StringProperty()
      album = db.ReferenceProperty(Album)
      artist = db.ReferenceProperty(Artist)


    # Register the appengine admin models.
    class AdminSong(appengine_admin.ModelAdmin):
      model = Song
      list_fields = ['title', 'genre', 'album']
      readonly_fields = ['artist']
      paginate_on = ['title']

    appengine_admin.admin_settings.PAGINATOR_PATH = 'path.to.paginator.Paginator'
    appengine_admin.register(AdminSong)

    app = WSGIApplication(
      routes=appengine_admin.get_application_routes(),
      config=app_config,
      debug=DEBUG)
    ```

5. To configure your settings, look at [`admin_settings.py`](https://github.com/humble/appengine-admin/blob/master/admin_settings.py)

Custom settings below (TODO: move to separate doc).

``ModelAdmin.pre_init``, ``ModelAdmin.pre_save``, ``ModelAdmin.post_save``
==========================================================================

Allow custom actions before initializing or saving the form, or after saving the form.

``ModelAdmin.custom_clean``
===========================

You can have a custom callback function to validate an individual field, example:

    ```python
    from django import forms

    class AdminSong(ModelAdmin):
      # ...
      def clean_title(self):
        title = self.cleaned_data.get('title')
        # do something here
        if len(title) < 5:
          raise forms.ValidationError('Title too short, must be at least 5 characters.')
        return title
      custom_clean = {
        'title': clean_title,
      }
    ```

6. Remember to update your index.yaml for each model class you are paginating. If you're just paginating by key, this should work:

    ```python
    - kind: Song
      properties:
      - name: __key__
        direction: desc
    ```

For more details, see the [QuickStart](http://code.google.com/p/appengine-admin/wiki/QuickStart) on Google Code.

## <span name="features">Features</span>

Most features are the ones listed on the original [Appengine Admin project page](http://code.google.com/p/appengine-admin/wiki/Features).

There may be more to come.

## <span name="dependencies">Dependencies</span>

* [gae_paginator](https://github.com/humble/gae_paginator)

## <span name="faq">FAQ</span>

1. __Why use it?__
   To get a nice admin to manage your data on production. And because it's better than updating your data from the remote shell or the built-in datastore viewer. And because it's hopefully gonna get even better :)

## <span name="todo">TODO</span>

See the [Issues](https://github.com/humble/appengine-admin/issues) on GitHub for details. And help out!
