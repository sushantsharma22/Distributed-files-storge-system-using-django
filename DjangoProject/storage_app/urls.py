from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_list, name='file_list'),
    path('upload/', views.upload_file, name='upload_file'),
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
