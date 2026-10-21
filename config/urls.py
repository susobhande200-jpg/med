
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.contrib.auth import views as auth_views


def health(request):
    return JsonResponse({
        "status": "ok",
        "service": "MedMitra"
    })


# Customize Django Admin headings
admin.site.site_header = "MedMitra Pharmacy Management"
admin.site.site_title = "MedMitra Administration"
admin.site.index_title = "Medicine catalogue, orders and inventory"


urlpatterns = [
    # Admin panel
    path("admin/", admin.site.urls),

    # User profiles
    path("profile/", include("profiles.urls")),

    # Pharmacy marketplace, account management and store inventory
    path("", include("marketplace.urls")),
    path("accounts/", include("accounts.urls")),
    path("pharmacy/", include("pharmacy.urls")),

    # Health check
    path("health/", health, name="health"),

    # Authentication
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    # Password reset
    path(
        "accounts/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html"
        ),
        name="password_reset",
    ),
]

# Uploaded homepage promotion images are served by Django only during local development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
