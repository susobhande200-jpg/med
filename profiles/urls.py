from django.urls import path
from . import views

urlpatterns = [
    path("", views.profile_overview, name="profile_overview"),
    path("edit/", views.profile_edit, name="profile_edit"),
    path("addresses/", views.address_list, name="profile_addresses"),
    path("addresses/add/", views.address_edit, name="profile_address_add"),
    path("addresses/<int:pk>/edit/", views.address_edit, name="profile_address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="profile_address_delete"),
    path("addresses/<int:pk>/default/", views.address_default, name="profile_address_default"),
    path("preferences/", views.profile_preferences, name="profile_preferences"),
    path("security/", views.profile_security, name="profile_security"),
    path("avatar/image/", views.avatar_image, name="profile_avatar_image"),
    path("avatar/remove/", views.remove_avatar, name="profile_avatar_remove"),
    path("export/", views.export_data, name="profile_export"),
    path("delete-request/", views.delete_request, name="profile_delete_request"),
    path("saved/", views.saved_items, name="profile_saved_items"),
    path("saved/pharmacy/<int:pk>/", views.save_pharmacy, name="profile_save_pharmacy"),
    path("saved/medicine/<int:pk>/", views.save_medicine, name="profile_save_medicine"),
]
