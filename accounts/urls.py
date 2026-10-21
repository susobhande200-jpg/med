from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("staff-dashboard/", views.role_dashboard, name="staff_dashboard"),
]
