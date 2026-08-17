from django.urls import path

from mysite import views

urlpatterns = [
    path("", views.index),
    path("figure", views.figure, name="figure"),
    path("figure-dtl", views.figure_dtl, name="figure_dtl"),
]
