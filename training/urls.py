from django.urls import path

from . import views

urlpatterns = [
    path("create_training_task/", views.create_training_task, name="create_training_task"),
    path("create_TextGeneration_task/", views.create_TextGeneration_task, name="create_TextGeneration_task"),
    path("create_Embedding_task/", views.create_Embedding_task, name="create_Embedding_task"),
    path("get_datasets_training_tasks/", views.get_datasets_training_tasks, name="get_datasets_training_tasks"),
    path("delete_training_task/", views.delete_training_task, name="delete_training_task"),
    path("update_training_status/", views.update_training_status, name="update_training_status"),
    path("insert_training_epoch_loss/", views.insert_training_epoch_loss, name="insert_training_epoch_loss"),
    path("get_training_epoch_loss/", views.get_training_epoch_loss, name="get_training_epoch_loss"),
    path("get_curr_epoch_loss/", views.get_curr_epoch_loss, name="get_curr_epoch_loss"),
    path("get_training_pid/", views.get_training_pid, name="get_training_pid"),
    path("start_resource_monitor/", views.start_resource_monitor, name="start_resource_monitor"),
    path("stop_resource_monitor/", views.stop_resource_monitor, name="stop_resource_monitor"),
    path("deploy_model/", views.deploy_model, name="deploy_model"),
    path("stop_deploy_model/", views.stop_deploy_model, name="stop_deploy_model"),
    path("embedding_deploy_model/", views.embedding_deploy_model, name="embedding_deploy_model"),
]