from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.project_list,   name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('projects/new/confirm/', views.project_create_confirm, name='project_create_confirm'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    # path('<int:pk>/export/', views.project_export, name='project_export'),
    path('<int:pk>/map/', views.project_map, name='project_map'),
    path('<int:pk>/assignments/<int:assignment_pk>/',
         views.assignment_detail, name='assignment_detail'),
    path('users/', views.user_manage, name='user_manage'),
    path('users/<int:pk>/edit/', views.user_edit,   name='user_edit'),
    path('import-users/edit/', views.import_users_edit, name='import_users_edit'),
    path('import-users/confirm/', views.import_users_confirm, name='import_users_confirm'),
    path('password-change/', 
         views.password_change, 
         name='password_change'),
    path('password-change/done/', 
         views.password_change_done, 
         name='password_change_done'),
     path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
     path('projects/<int:pk>/complete/', views.project_complete, name='project_complete'),


]
