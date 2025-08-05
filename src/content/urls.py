from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("", views.NewsListView.as_view(), name="list"),
    path("archive/", views.NewsArchiveView.as_view(), name="archive"),
    path("author/<int:author_id>/", views.NewsByAuthorView.as_view(),
         name="by_author"),
    path("latest/", views.LatestNewsView.as_view(), name="latest"),
    path("<slug:slug>/", views.NewsDetailView.as_view(), name="detail"),
]
