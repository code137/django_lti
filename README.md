# django_lti

Using pylti (built on flask) as a base I've converted it to run with a django decorator and modified oauth and oauth2 to work with python 3.4.0

With an empty new django (1.9/python 3.4.0 3.5.0 tested) project with migrations run and django sessions available

clone into the existing django application
```
git clone https://github.com/code137/django_lti.git lti
```
```
pip install -r requirements.txt
```

Add lti to the list of INSTALLED_APPS in the main settings.py

Disable XFrameOptionsMiddleware
```python
# 'django.middleware.clickjacking.XFrameOptionsMiddleware’, in MIDDLEWARE_CLASSES
````
Modify the main applications urls:

```python
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^lti/', include('lti.urls')),
]
```

Run the server and test on http://ltiapps.net/test/tc.php using the consumer key and secret against localhost.

There are modified oauth and oauth2 libraries in the dependencies that were required after modfifying pylti to work with django 1.9 and python 3.4.0+.

It's a bit messy at the moment...
