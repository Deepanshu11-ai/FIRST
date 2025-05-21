from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/manage_user/', views.admin_manage_user, name='admin_manage_user'),
    path('admin/edit_user/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),
     path('admin/delete_user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/complete_appointment/<int:appointment_id>/', views.complete_appointment, name='complete_appointment'),
    path('doctor/cancel_appointment/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('doctor/manage_availability/', views.manage_availability, name='manage_availability'),

]
