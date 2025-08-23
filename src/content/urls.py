from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("", views.NewsListView.as_view(), name="list"),
    path("archive/", views.NewsArchiveView.as_view(), name="archive"),
    path("author/<int:author_id>/", views.NewsByAuthorView.as_view(),
         name="by_author"),
    path("latest/", views.LatestNewsView.as_view(), name="latest"),
    path("archive/<int:year>/<int:month>/", views.NewsByMonthView.as_view(),
         name="news_by_month"),
    path("search/", views.global_search_view, name="global_search"),
    path("programs/", views.ProgramListView.as_view(), name="program_list"),
    path("programs/<int:pk>/", views.ProgramDetailView.as_view(),
         name="program_detail"),
    path("<slug:slug>/", views.NewsDetailView.as_view(), name="detail"),
]
