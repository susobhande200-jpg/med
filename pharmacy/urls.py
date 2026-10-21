from django.urls import path
from . import views
urlpatterns=[path('',views.dashboard,name='pharmacy_dashboard'),path('medicines/',views.medicine_list,name='pharmacy_medicines'),path('medicines/add/',views.medicine_add,name='pharmacy_medicine_add'),path('medicines/<int:pk>/edit/',views.medicine_edit,name='pharmacy_medicine_edit'),path('stock/',views.stock_movement_list,name='pharmacy_stock'),path('sales/new/',views.sale_create,name='pharmacy_sale')]
