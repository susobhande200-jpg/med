from django.contrib import admin
from .models import (
    MedicineCategory, MedicineProduct, Pharmacy, PharmacyListing, Prescription,
    CartItem, MarketplaceOrder, MarketplaceOrderItem, OrderStatusEvent, MarketplaceAuditLog,
    HomepagePromotion, HomepageTrustMetric, HomepageTestimonial, HomepageSearchTerm, HomepageEditorialSection,
    FooterSocialLink,
)


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("active",)


@admin.register(MedicineProduct)
class MedicineProductAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "generic_name", "strength", "dosage_form", "category", "requires_prescription", "active")
    search_fields = ("brand_name", "generic_name", "manufacturer")
    list_filter = ("category", "dosage_form", "requires_prescription", "active")


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "pincode", "verification_status", "offers_delivery", "offers_pickup")
    list_filter = ("verification_status", "city", "offers_delivery", "offers_pickup")
    search_fields = ("name", "owner__username", "licence_number", "pincode")
    readonly_fields = ("created_at", "updated_at", "verified_at")


@admin.register(PharmacyListing)
class PharmacyListingAdmin(admin.ModelAdmin):
    list_display = ("product", "pharmacy", "mrp", "selling_price", "available_quantity", "reserved_quantity", "expiry_date", "active", "last_stock_update")
    list_filter = ("active", "pharmacy__verification_status", "product__category")
    search_fields = ("product__brand_name", "product__generic_name", "pharmacy__name", "batch_number")
    readonly_fields = ("last_stock_update", "created_at", "updated_at")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "status", "reviewed_by", "reviewed_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("owner__username", "owner__email")
    readonly_fields = ("created_at", "reviewed_at")


class MarketplaceOrderItemInline(admin.TabularInline):
    model = MarketplaceOrderItem
    extra = 0
    readonly_fields = ("product_name_snapshot", "quantity", "unit_price", "mrp_snapshot")


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer", "pharmacy", "status", "fulfilment", "total", "created_at")
    list_filter = ("status", "fulfilment", "created_at")
    search_fields = ("reference", "customer__username", "pharmacy__name")
    readonly_fields = ("reference", "subtotal", "delivery_fee", "total", "created_at", "updated_at")
    inlines = (MarketplaceOrderItemInline,)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("customer", "listing", "quantity", "added_at")
    search_fields = ("customer__username", "listing__product__brand_name")


@admin.register(OrderStatusEvent)
class OrderStatusEventAdmin(admin.ModelAdmin):
    list_display = ("order", "actor", "old_status", "new_status", "created_at")
    list_filter = ("new_status", "created_at")
    readonly_fields = ("order", "actor", "old_status", "new_status", "note", "created_at")


@admin.register(MarketplaceAuditLog)
class MarketplaceAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "object_type", "object_id", "details")
    readonly_fields = ("actor", "action", "object_type", "object_id", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SuperuserOnlyModelAdmin(admin.ModelAdmin):
    """Homepage content may only be managed by Django superusers."""
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser


@admin.register(HomepagePromotion)
class HomepagePromotionAdmin(SuperuserOnlyModelAdmin):
    list_display = ("title", "is_active", "sort_order", "starts_at", "ends_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle", "alt_text")
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Banner content", {"fields": ("title", "subtitle", "image", "alt_text", "target_url", "button_label")}),
        ("Display and scheduling", {"fields": ("is_active", "sort_order", "starts_at", "ends_at")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(HomepageTrustMetric)
class HomepageTrustMetricAdmin(SuperuserOnlyModelAdmin):
    list_display = ("value", "label", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("value", "label", "detail")
    list_editable = ("is_active", "sort_order")


@admin.register(HomepageTestimonial)
class HomepageTestimonialAdmin(SuperuserOnlyModelAdmin):
    list_display = ("customer_name", "rating", "review_date", "is_published", "sort_order")
    list_filter = ("is_published", "rating")
    search_fields = ("customer_name", "location_label", "quote")
    list_editable = ("is_published", "sort_order")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Review", {"fields": ("customer_name", "location_label", "review_date", "rating", "quote")}),
        ("Publishing", {"fields": ("is_published", "sort_order")}),
        ("Audit", {"fields": ("created_at",)}),
    )


@admin.register(HomepageSearchTerm)
class HomepageSearchTermAdmin(SuperuserOnlyModelAdmin):
    list_display = ("term", "section", "is_active", "sort_order")
    list_filter = ("section", "is_active")
    search_fields = ("term",)
    list_editable = ("is_active", "sort_order")


@admin.register(HomepageEditorialSection)
class HomepageEditorialSectionAdmin(SuperuserOnlyModelAdmin):
    list_display = ("title", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "body", "seo_description")
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Content", {"fields": ("eyebrow", "title", "body", "button_label", "button_url")}),
        ("SEO and publishing", {"fields": ("seo_description", "is_active", "sort_order")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

@admin.register(FooterSocialLink)
class FooterSocialLinkAdmin(SuperuserOnlyModelAdmin):
    list_display = ("platform", "label", "url", "is_active", "sort_order", "updated_at")
    list_filter = ("platform", "is_active", "open_in_new_tab")
    search_fields = ("platform", "label", "url")
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Social profile", {"fields": ("platform", "label", "url", "open_in_new_tab")}),
        ("Footer display", {"fields": ("is_active", "sort_order")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

