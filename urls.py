from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^is_up$', views.is_up, name='is_up'),
    url(r'^add', views.add, name='add'),
    url(r'^grade', views.grade, name='grade'),
    url(r'^instructor', views.instructor, name='instructor'),
    url(r'^staff', views.staff, name='staff'),
]