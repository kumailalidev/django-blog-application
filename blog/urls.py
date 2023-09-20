from django.urls import path
from . import views
from .feeds import LatestPostFeed

app_name = "blog"

urlpatterns = [
    # Function based post list view
    path("", views.post_list, name="post_list"),
    path("tag/<slug:tag_slug>/", views.post_list, name="post_list_by_tag"),
    # Class based post list view
    # path("", views.PostListView.as_view(), name="post_list"),
    path(
        "<int:year>/<int:month>/<int:day>/<slug:post>/",
        views.post_detail,
        name="post_detail",
    ),
    path("<int:post_id>/share/", views.post_share, name="post_share"),
    path("<int:post_id>", views.post_comment, name="post_comment"),
    path("feed/", LatestPostFeed(), name="post_feed"),
    path("search/", views.post_search, name="post_search"),
]
