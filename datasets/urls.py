from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("get_user_datasets/", views.get_user_datasets, name="get_user_datasets"),
    path("create_project/", views.create_project, name="create_project"),
    path("get_user_projects/", views.get_user_projects, name="get_user_projects"),
    path("delete_project/", views.delete_project, name="delete_project"),
    path("delete_dataset/", views.delete_dataset, name="delete_dataset"),
    path("get_project/", views.get_project, name="get_project"),
    path("get_dataset/", views.get_dataset, name="get_dataset"),
    path("get_minio_links/", views.get_minio_links, name="get_minio_links"),
    path("get_dataset_is_upload/", views.get_dataset_is_upload, name="get_dataset_is_upload"),



    
    path("create_dataset/", views.create_dataset, name="create_dataset"),
    path("add_data_to_dataset/", views.add_data_to_dataset, name="add_data_to_dataset"),
    path("get_dataset_list/", views.get_dataset_list, name="get_dataset_list"),
    path("get_dataset_detail/", views.get_dataset_detail, name="get_dataset_detail"),
    path("delete_dataset_api/", views.delete_dataset_api, name="delete_dataset_api"),
    path("get_match_list/", views.get_match_list, name="get_match_list"),
    path("remove_data_from_dataset/", views.remove_data_from_dataset, name="remove_data_from_dataset"),
    # path("get_match_by_date/", views.get_match_by_date, name="get_match_by_date"),
    # path("delete_match/", views.delete_match, name="delete_match"),
    # path("temp_test/", views.temp_test, name="temp_test"),
]
