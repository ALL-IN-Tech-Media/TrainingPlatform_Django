from django.urls import path

from . import views

urlpatterns = [
    path("get_task_model_list/", views.get_task_model_list, name="get_task_model_list"),
    path("add_new_model/", views.add_new_model, name="add_new_model"),
    path("get_model_list/", views.get_model_list, name="get_model_list"),
    path("cancel_download/", views.cancel_download, name="cancel_download"),
]