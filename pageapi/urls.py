from django.urls import path
from . import views

urlpatterns = [
    path("health", views.health_check, name="health_check"),
    path("page/<str:page_id>", views.get_page_info, name="get_page_info"),
    path("page/<str:page_id>/posts", views.page_posts, name="page_posts"),
    path("page/post/<str:post_id>", views.delete_page_post, name="delete_page_post"),
    path("page/post/<str:post_id>/comments", views.get_post_comments, name="get_post_comments"),
    path("page/post/<str:post_id>/likes", views.get_post_likes, name="get_post_likes"),
    path("page/<str:page_id>/insights", views.get_page_insights, name="get_page_insights"),
    path("admin/events", views.list_inbound_events, name="list_inbound_events"),
    path("admin/comments/history", views.list_comment_history, name="list_comment_history"),
    path("admin/blacklist", views.list_blacklist, name="list_blacklist"),
    path("admin/users/block", views.block_user, name="block_user"),
    path("admin/users/unblock", views.unblock_user, name="unblock_user"),
    path("admin/blacklist/add", views.add_blacklist_user, name="add_blacklist_user"),
]