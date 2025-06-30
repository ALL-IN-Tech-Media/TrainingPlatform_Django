from django.urls import path

from . import views

urlpatterns = [
    path("create_training_task/", views.create_training_task, name="create_training_task"),
    path("get_datasets_training_tasks/", views.get_datasets_training_tasks, name="get_datasets_training_tasks"),
    path("delete_training_task/", views.delete_training_task, name="delete_training_task"),
    path("update_training_status/", views.update_training_status, name="update_training_status"),
    path("insert_training_epoch_loss/", views.insert_training_epoch_loss, name="insert_training_epoch_loss"),
    path("get_training_epoch_loss/", views.get_training_epoch_loss, name="get_training_epoch_loss"),
    path("get_curr_epoch_loss/", views.get_curr_epoch_loss, name="get_curr_epoch_loss"),
]