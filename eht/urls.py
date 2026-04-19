from django.urls import path
from . import views

# app_name = "eht"
urlpatterns = [  
    path('', views.index, name ='index'),
    path('create-project-data/', views.create_project_data, name='create_project_data'),   
    path('edit-project-data/<str:project_id>/', views.update_project_data, name='update_project_data'),
    # path('upload-input-file/', views.upload_input, name='upload_input_file'),
    path('upload-input-file/', views.calculate_view, name='calculate_view'),
    path('input-lines/', views.import_input_view, name='import_input_view'),
    path('input-lines/export/', views.input_data_export_view, name='input_data_export_view'),
    path('results/', views.result_view, name='result_view'),
    path('results/export/', views.result_export_view, name='result_export_view'),
    path('boq/', views.boq_view, name='boq_view'),
    path('boq/line-detail/', views.boq_line_detail_view, name='boq_line_detail_view'),
    path('boq/export/', views.boq_export_view, name='boq_export_view'),
    path('download-template-file/', views.download_template, name='download_template_file'),
    path('confirm-valid-data/', views.confirm_valid_data, name='confirm_valid_data'),
    path('download-error-file/<str:file_name>/', views.download_error_file, name='download_error_file'),    
    path('base/', views.base, name='base'),    
    path('login/', views.my_login, name='my_login'),    
    path('logout/', views.my_logout, name='my_logout'),    
    path('register/', views.my_register, name='my_register'),
    path('sld/', views.sld, name='sld'),
]
