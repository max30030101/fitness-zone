from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("about/", views.about, name="about"),
    path("mindset/", views.mindset, name="mindset"),
    path("mindset/<slug:slug>/", views.article, name="article"),
]
