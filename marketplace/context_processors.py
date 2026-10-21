def marketplace_ui(request):
    cart_count = 0
    has_pharmacy = False
    has_pharmacy_staff = False
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        try:
            cart_count = sum(request.user.marketplace_cart_items.values_list("quantity", flat=True))
        except Exception:
            cart_count = 0
        try:
            has_pharmacy = request.user.owned_pharmacies.exists()
        except Exception:
            has_pharmacy = False
        try:
            from accounts.models import StaffProfile
            has_pharmacy_staff = StaffProfile.objects.filter(
                user=request.user, is_approved=True,
                role__in=[StaffProfile.Role.PHARMACIST, StaffProfile.Role.STORE_MANAGER],
            ).exists()
        except Exception:
            has_pharmacy_staff = False
    try:
        from .models import FooterSocialLink
        footer_social_links = FooterSocialLink.objects.filter(is_active=True)
    except Exception:
        # Keep public pages available during fresh installs before migrations run.
        footer_social_links = []

    return {
        "marketplace_cart_count": cart_count,
        "has_owned_pharmacy": has_pharmacy,
        "has_pharmacy_staff": has_pharmacy_staff,
        "footer_social_links": footer_social_links,
    }
