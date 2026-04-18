from django.urls import path
from . import views

urlpatterns = [
    path("page/<str:page_id>", views.get_page_info, name="get_page_info"),
    path("page/<str:page_id>/posts", views.page_posts, name="page_posts"),
    path("page/post/<str:post_id>", views.delete_page_post, name="delete_page_post"),
    path("page/post/<str:post_id>/comments", views.get_post_comments, name="get_post_comments"),
    path("page/post/<str:post_id>/likes", views.get_post_likes, name="get_post_likes"),
    path("page/<str:page_id>/insights", views.get_page_insights, name="get_page_insights"),
]