from decimal import Decimal
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count, F, DecimalField, ExpressionWrapper
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PharmacyRegistrationForm, ListingForm, PrescriptionUploadForm, CartAddForm, CheckoutForm
from .models import (
    MedicineCategory, MedicineProduct, Pharmacy, PharmacyListing, Prescription,
    CartItem, MarketplaceOrder, MarketplaceOrderItem, OrderStatusEvent, MarketplaceAuditLog,
    HomepagePromotion, HomepageTrustMetric, HomepageTestimonial, HomepageSearchTerm, HomepageEditorialSection,
)


def _write_audit(actor, action, obj, details=""):
    """Record sensitive marketplace actions without logging health-document contents."""
    MarketplaceAuditLog.objects.create(
        actor=actor, action=action, object_type=obj._meta.label_lower,
        object_id=str(obj.pk), details=str(details)[:500],
    )


def _public_listings():
    return PharmacyListing.objects.filter(
        active=True,
        pharmacy__verification_status=Pharmacy.VerificationStatus.APPROVED,
        product__active=True,
    ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.localdate())).select_related("product", "product__category", "pharmacy")


def home(request):
    now = timezone.now()
    featured = _public_listings().filter(available_quantity__gt=F("reserved_quantity")).order_by("-last_stock_update")[:8]
    categories = MedicineCategory.objects.filter(active=True)[:8]
    pharmacy_count = Pharmacy.objects.filter(verification_status=Pharmacy.VerificationStatus.APPROVED).count()
    product_count = MedicineProduct.objects.filter(active=True).count()

    promotions = HomepagePromotion.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    ).order_by("sort_order", "id")
    metrics = HomepageTrustMetric.objects.filter(is_active=True).order_by("sort_order", "id")
    testimonials = HomepageTestimonial.objects.filter(is_published=True).order_by("sort_order", "-review_date", "id")
    search_terms = HomepageSearchTerm.objects.filter(is_active=True).order_by("sort_order", "term")
    editorial_sections = HomepageEditorialSection.objects.filter(is_active=True).order_by("sort_order", "id")
    homepage_meta_description = editorial_sections.exclude(seo_description="").values_list("seo_description", flat=True).first()

    return render(request, "marketplace/home.html", {
        "featured": featured,
        "categories": categories,
        "pharmacy_count": pharmacy_count,
        "product_count": product_count,
        "homepage_promotions": promotions,
        "homepage_metrics": metrics,
        "homepage_testimonials": testimonials,
        "top_healthcare_terms": search_terms.filter(section=HomepageSearchTerm.Section.HEALTHCARE),
        "top_medicine_terms": search_terms.filter(section=HomepageSearchTerm.Section.MEDICINES),
        "top_searched_terms": search_terms.filter(section=HomepageSearchTerm.Section.SEARCHED),
        "top_vaccine_terms": search_terms.filter(section=HomepageSearchTerm.Section.VACCINES),
        "homepage_editorial_sections": editorial_sections,
        "homepage_meta_description": homepage_meta_description,
    })


def medicine_search(request):
    listings = _public_listings().filter(available_quantity__gt=F("reserved_quantity"))
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    pincode = request.GET.get("pincode", "").strip()
    fulfilment = request.GET.get("fulfilment", "").strip()
    sort = request.GET.get("sort", "relevance").strip()
    if q:
        listings = listings.filter(
            Q(product__brand_name__icontains=q)
            | Q(product__generic_name__icontains=q)
            | Q(product__strength__icontains=q)
            | Q(product__manufacturer__icontains=q)
        )
    if category:
        listings = listings.filter(product__category__slug=category)
    if pincode:
        listings = listings.filter(pharmacy__pincode__icontains=pincode)
    if fulfilment == "delivery":
        listings = listings.filter(pharmacy__offers_delivery=True)
    elif fulfilment == "pickup":
        listings = listings.filter(pharmacy__offers_pickup=True)
    if sort == "price_low":
        listings = listings.order_by("selling_price", "product__brand_name")
    elif sort == "discount":
        listings = listings.annotate(discount_value=ExpressionWrapper(100 * (F("mrp") - F("selling_price")) / F("mrp"), output_field=DecimalField(max_digits=7, decimal_places=2))).order_by("-discount_value", "selling_price")
    else:
        listings = listings.order_by("product__brand_name", "selling_price")
    return render(request, "marketplace/medicine_search.html", {
        "listings": listings[:100], "q": q, "categories": MedicineCategory.objects.filter(active=True),
        "selected_category": category, "pincode": pincode, "fulfilment": fulfilment, "sort": sort,
        "result_count": listings.count(),
    })


def medicine_detail(request, pk):
    product = get_object_or_404(MedicineProduct, pk=pk, active=True)
    listings = _public_listings().filter(product=product).order_by("selling_price", "pharmacy__name")
    return render(request, "marketplace/medicine_detail.html", {"product": product, "listings": listings})


def pharmacy_finder(request):
    pharmacies = Pharmacy.objects.filter(verification_status=Pharmacy.VerificationStatus.APPROVED).annotate(
        live_listings=Count(
            "listings",
            filter=Q(
                listings__active=True, listings__available_quantity__gt=F("listings__reserved_quantity"),
                listings__product__active=True,
            ) & (Q(listings__expiry_date__isnull=True) | Q(listings__expiry_date__gte=timezone.localdate())),
            distinct=True,
        ),
    )
    q = request.GET.get("q", "").strip()
    pincode = request.GET.get("pincode", "").strip()
    delivery = request.GET.get("delivery", "")
    if q:
        pharmacies = pharmacies.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(locality__icontains=q) | Q(address__icontains=q))
    if pincode:
        pharmacies = pharmacies.filter(pincode__icontains=pincode)
    if delivery == "yes":
        pharmacies = pharmacies.filter(offers_delivery=True)
    pharmacies = pharmacies.order_by("city", "name")
    map_points = []
    for p in pharmacies:
        if p.latitude is not None and p.longitude is not None:
            map_points.append({"name": p.name, "lat": float(p.latitude), "lng": float(p.longitude), "address": p.full_address, "url": f"/pharmacies/{p.slug}/"})
    return render(request, "marketplace/pharmacy_finder.html", {
        "pharmacies": pharmacies, "q": q, "pincode": pincode, "delivery": delivery,
        "map_points": map_points,
    })


def pharmacy_detail(request, slug):
    pharmacy = get_object_or_404(Pharmacy, slug=slug, verification_status=Pharmacy.VerificationStatus.APPROVED)
    listings = _public_listings().filter(pharmacy=pharmacy).order_by("product__brand_name")
    return render(request, "marketplace/pharmacy_detail.html", {"pharmacy": pharmacy, "listings": listings})


@login_required
def retailer_register(request):
    if request.method == "POST":
        form = PharmacyRegistrationForm(request.POST)
        if form.is_valid():
            pharmacy = form.save(commit=False)
            pharmacy.owner = request.user
            pharmacy.verification_status = Pharmacy.VerificationStatus.PENDING
            pharmacy.save()
            _write_audit(request.user, "pharmacy_submitted", pharmacy, "Submitted for verification")
            messages.success(request, "Pharmacy profile submitted. It will appear in public search after administrator verification.")
            return redirect("retailer_dashboard")
    else:
        form = PharmacyRegistrationForm()
    return render(request, "marketplace/retailer_register.html", {"form": form})


def _owned_pharmacy(request, pharmacy_id=None):
    qs = Pharmacy.objects.filter(owner=request.user).order_by("created_at")
    if request.user.is_staff or request.user.is_superuser:
        qs = Pharmacy.objects.all().order_by("created_at")
    if pharmacy_id:
        return get_object_or_404(qs, pk=pharmacy_id)
    return qs.first()


@login_required
def retailer_dashboard(request):
    pharmacies = Pharmacy.objects.filter(owner=request.user).order_by("created_at")
    if request.user.is_staff or request.user.is_superuser:
        pharmacies = Pharmacy.objects.all().order_by("created_at")
    if not pharmacies.exists():
        return render(request, "marketplace/retailer_dashboard.html", {"pharmacies": pharmacies, "pharmacy": None})
    pharmacy = _owned_pharmacy(request, request.GET.get("pharmacy"))
    listings = PharmacyListing.objects.filter(pharmacy=pharmacy).select_related("product")
    orders = MarketplaceOrder.objects.filter(pharmacy=pharmacy).select_related("customer")[:8]
    today = timezone.localdate()
    context = {
        "pharmacies": pharmacies, "pharmacy": pharmacy, "listings": listings,
        "listing_count": listings.count(),
        "low_stock_count": listings.filter(available_quantity__lte=5, active=True).count(),
        "out_of_stock_count": listings.filter(available_quantity__lte=F("reserved_quantity"), active=True).count(),
        "near_expiry_count": listings.filter(active=True, available_quantity__gt=F("reserved_quantity"), expiry_date__gte=today, expiry_date__lte=today + timedelta(days=60)).count(),
        "expired_stock_count": listings.filter(active=True, available_quantity__gt=F("reserved_quantity"), expiry_date__lt=today).count(),
        "pending_orders": MarketplaceOrder.objects.filter(pharmacy=pharmacy, status=MarketplaceOrder.Status.PENDING).count(),
        "orders": orders,
    }
    return render(request, "marketplace/retailer_dashboard.html", context)


@login_required
def retailer_listings(request):
    pharmacy = _owned_pharmacy(request, request.GET.get("pharmacy"))
    if pharmacy is None:
        messages.info(request, "Register your pharmacy to manage inventory.")
        return redirect("retailer_register")
    listings = PharmacyListing.objects.filter(pharmacy=pharmacy).select_related("product", "product__category").order_by("product__brand_name")
    q = request.GET.get("q", "").strip()
    if q:
        listings = listings.filter(Q(product__brand_name__icontains=q) | Q(product__generic_name__icontains=q))
    return render(request, "marketplace/retailer_listings.html", {"pharmacy": pharmacy, "listings": listings, "q": q})


@login_required
def retailer_listing_form(request, pk=None):
    if pk:
        listing = get_object_or_404(PharmacyListing, pk=pk)
        if listing.pharmacy.owner_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        pharmacy = listing.pharmacy
    else:
        pharmacy = _owned_pharmacy(request, request.GET.get("pharmacy"))
        listing = None
        if pharmacy is None:
            messages.info(request, "Register your pharmacy first.")
            return redirect("retailer_register")
        if not pharmacy.verified:
            messages.error(request, "Only verified pharmacies can publish medicine listings.")
            return redirect("retailer_dashboard")
    if request.method == "POST":
        form = ListingForm(request.POST, instance=listing)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.pharmacy = pharmacy
            saved.save()
            _write_audit(request.user, "listing_saved", saved, f"Pharmacy #{pharmacy.pk}; product #{saved.product_id}; active={saved.active}")
            messages.success(request, "Medicine listing saved.")
            return redirect(f"/retailer/listings/?pharmacy={pharmacy.pk}")
    else:
        form = ListingForm(instance=listing)
    return render(request, "marketplace/listing_form.html", {"form": form, "pharmacy": pharmacy, "listing": listing})


@login_required
def retailer_orders(request):
    pharmacies = Pharmacy.objects.filter(owner=request.user)
    if request.user.is_staff or request.user.is_superuser:
        pharmacies = Pharmacy.objects.all()
    orders = MarketplaceOrder.objects.filter(pharmacy__in=pharmacies).select_related("customer", "pharmacy").prefetch_related("items")
    status = request.GET.get("status", "").strip()
    if status in MarketplaceOrder.Status.values:
        orders = orders.filter(status=status)
    return render(request, "marketplace/retailer_orders.html", {"orders": orders[:150], "status": status, "statuses": MarketplaceOrder.Status.choices})


def _is_pharmacy_owner(user, pharmacy):
    return bool(user.is_staff or user.is_superuser or pharmacy.owner_id == user.id)


def _release_order_reservations(order, consume=False):
    for item in order.items.select_related("listing").all():
        listing = PharmacyListing.objects.select_for_update().get(pk=item.listing_id)
        listing.reserved_quantity = max(0, listing.reserved_quantity - item.quantity)
        if consume:
            listing.available_quantity = max(0, listing.available_quantity - item.quantity)
        listing.save(update_fields=["reserved_quantity", "available_quantity", "last_stock_update", "updated_at"])


def _transition_order(order, new_status, actor, note=""):
    old = order.status
    allowed = {
        MarketplaceOrder.Status.PENDING: {MarketplaceOrder.Status.ACCEPTED, MarketplaceOrder.Status.REJECTED, MarketplaceOrder.Status.CANCELLED},
        MarketplaceOrder.Status.ACCEPTED: {MarketplaceOrder.Status.PROCESSING, MarketplaceOrder.Status.CANCELLED},
        MarketplaceOrder.Status.PROCESSING: {MarketplaceOrder.Status.READY, MarketplaceOrder.Status.OUT_FOR_DELIVERY, MarketplaceOrder.Status.CANCELLED},
        MarketplaceOrder.Status.READY: {MarketplaceOrder.Status.COMPLETED, MarketplaceOrder.Status.CANCELLED},
        MarketplaceOrder.Status.OUT_FOR_DELIVERY: {MarketplaceOrder.Status.COMPLETED, MarketplaceOrder.Status.REFUND_PENDING},
        MarketplaceOrder.Status.REFUND_PENDING: {MarketplaceOrder.Status.REFUNDED},
    }
    if new_status not in allowed.get(old, set()):
        new_label = dict(MarketplaceOrder.Status.choices).get(new_status, "that status")
        raise ValidationError(f"Cannot change an order from {order.get_status_display()} to {new_label}.")
    if new_status == MarketplaceOrder.Status.ACCEPTED:
        if order.items.filter(listing__product__requires_prescription=True).exists():
            if not order.prescription or order.prescription.status != Prescription.Status.APPROVED:
                raise ValidationError("The linked prescription must be approved before this order can be accepted.")
        if order.items.filter(listing__expiry_date__lt=timezone.localdate()).exists():
            raise ValidationError("This order contains an expired batch and cannot be accepted.")
    if new_status == MarketplaceOrder.Status.COMPLETED:
        if order.items.filter(listing__expiry_date__lt=timezone.localdate()).exists():
            raise ValidationError("This order contains an expired batch and cannot be completed.")
        _release_order_reservations(order, consume=True)
    elif new_status in {MarketplaceOrder.Status.REJECTED, MarketplaceOrder.Status.CANCELLED} and old in {
        MarketplaceOrder.Status.PENDING, MarketplaceOrder.Status.ACCEPTED, MarketplaceOrder.Status.PROCESSING, MarketplaceOrder.Status.READY
    }:
        _release_order_reservations(order, consume=False)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    OrderStatusEvent.objects.create(order=order, actor=actor, old_status=old, new_status=new_status, note=note[:300])
    _write_audit(actor, "order_status_changed", order, f"{old} -> {new_status}")


@login_required
@require_POST
def retailer_order_status(request, pk):
    order = get_object_or_404(MarketplaceOrder.objects.select_related("pharmacy", "prescription"), pk=pk)
    if not _is_pharmacy_owner(request.user, order.pharmacy):
        raise PermissionDenied
    new_status = request.POST.get("status", "")
    try:
        with transaction.atomic():
            order = MarketplaceOrder.objects.select_for_update().get(pk=order.pk)
            _transition_order(order, new_status, request.user, request.POST.get("note", ""))
        messages.success(request, f"Order {order.reference} updated to {order.get_status_display()}.")
    except (ValidationError, ValueError) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
    return redirect("retailer_orders")


@login_required
@require_POST
def customer_cancel_order(request, pk):
    order = get_object_or_404(MarketplaceOrder.objects.select_related("pharmacy"), pk=pk)
    if order.customer_id != request.user.id:
        raise PermissionDenied
    try:
        with transaction.atomic():
            order = MarketplaceOrder.objects.select_for_update().get(pk=order.pk)
            _transition_order(order, MarketplaceOrder.Status.CANCELLED, request.user, "Cancelled by customer")
        messages.success(request, f"Order {order.reference} cancelled. The stock reservation was released.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("customer_dashboard")


@login_required
def customer_dashboard(request):
    orders = MarketplaceOrder.objects.filter(customer=request.user).select_related("pharmacy", "prescription").prefetch_related("items")
    prescriptions = Prescription.objects.filter(owner=request.user)
    return render(request, "marketplace/customer_dashboard.html", {"orders": orders[:100], "prescriptions": prescriptions[:10]})


@login_required
def prescription_list(request):
    prescriptions = Prescription.objects.filter(owner=request.user)
    return render(request, "marketplace/prescriptions.html", {"prescriptions": prescriptions})


@login_required
def prescription_upload(request):
    if request.method == "POST":
        form = PrescriptionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.owner = request.user
            prescription.original_filename = request.FILES["file"].name[:255]
            prescription.save()
            messages.success(request, "Prescription uploaded privately. A pharmacy must review it before a prescription-required order can be accepted.")
            return redirect("prescriptions")
    else:
        form = PrescriptionUploadForm()
    return render(request, "marketplace/prescription_upload.html", {"form": form})


@login_required
def prescription_download(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    allowed = prescription.owner_id == request.user.id or request.user.is_staff or request.user.is_superuser
    if not allowed:
        allowed = MarketplaceOrder.objects.filter(prescription=prescription, pharmacy__owner=request.user).exists()
    if not allowed:
        raise PermissionDenied
    try:
        response = FileResponse(prescription.file.open("rb"), as_attachment=True, filename=prescription.original_filename or "prescription")
    except (FileNotFoundError, ValueError):
        raise Http404("Prescription file is unavailable.")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def prescription_review(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    owner_pharmacies = Pharmacy.objects.filter(owner=request.user)
    permitted = request.user.is_staff or request.user.is_superuser or MarketplaceOrder.objects.filter(prescription=prescription, pharmacy__in=owner_pharmacies).exists()
    if not permitted:
        raise PermissionDenied
    status = request.POST.get("status", "")
    if status not in {Prescription.Status.APPROVED, Prescription.Status.REJECTED, Prescription.Status.CLARIFICATION}:
        messages.error(request, "Choose a valid review outcome.")
    else:
        prescription.status = status
        prescription.review_note = request.POST.get("review_note", "")[:500]
        prescription.reviewed_by = request.user
        prescription.reviewed_at = timezone.now()
        prescription.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])
        _write_audit(request.user, "prescription_reviewed", prescription, f"Outcome={status}")
        messages.success(request, "Prescription review saved.")
    return redirect("retailer_orders")


@login_required
@require_POST
def cart_add(request, listing_id):
    listing = get_object_or_404(_public_listings(), pk=listing_id)
    form = CartAddForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid quantity between 1 and 50.")
        return redirect(request.META.get("HTTP_REFERER", "medicine_search"))
    qty = form.cleaned_data["quantity"]
    existing = CartItem.objects.filter(customer=request.user, listing=listing).first()
    target_qty = qty + existing.quantity if existing else qty
    if target_qty > 50 or not listing.in_stock or target_qty > listing.sellable_quantity:
        messages.error(request, "The requested quantity is not currently available. Please refresh stock information.")
        return redirect(request.META.get("HTTP_REFERER", "medicine_search"))
    item, created = CartItem.objects.get_or_create(customer=request.user, listing=listing, defaults={"quantity": qty})
    if not created:
        item.quantity = target_qty
        item.save(update_fields=["quantity"])
    messages.success(request, "Added to your cart. Cart items from each pharmacy are checked out separately.")
    return redirect("cart_detail")


@login_required
def cart_detail(request):
    items = list(CartItem.objects.filter(customer=request.user).select_related("listing__product", "listing__pharmacy"))
    grouped = {}
    for item in items:
        pharmacy = item.listing.pharmacy
        group = grouped.setdefault(pharmacy.pk, {"pharmacy": pharmacy, "items": [], "subtotal": Decimal("0.00")})
        group["items"].append(item)
        group["subtotal"] += item.subtotal
    groups = list(grouped.values())
    return render(request, "marketplace/cart.html", {"groups": groups, "item_count": len(items)})


@login_required
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(CartItem.objects.select_related("listing"), pk=pk, customer=request.user)
    try:
        qty = int(request.POST.get("quantity", "0"))
    except ValueError:
        qty = 0
    if qty < 1 or qty > 50 or qty > item.listing.sellable_quantity:
        messages.error(request, "Choose a quantity available from this pharmacy (1–50).")
    else:
        item.quantity = qty
        item.save(update_fields=["quantity"])
        messages.success(request, "Cart updated.")
    return redirect("cart_detail")


@login_required
@require_POST
def cart_remove(request, pk):
    get_object_or_404(CartItem, pk=pk, customer=request.user).delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart_detail")


@login_required
def checkout(request, pharmacy_id):
    pharmacy = get_object_or_404(Pharmacy, pk=pharmacy_id, verification_status=Pharmacy.VerificationStatus.APPROVED)
    cart_items = list(CartItem.objects.filter(customer=request.user, listing__pharmacy=pharmacy).select_related("listing__product", "listing__pharmacy"))
    if not cart_items:
        messages.info(request, "There are no cart items for this pharmacy.")
        return redirect("cart_detail")
    form = CheckoutForm(request.POST or None, customer=request.user, pharmacy=pharmacy)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                # Lock and refresh the cart rows too, so simultaneous double-submits cannot
                # create two orders from the same cart after the first transaction clears it.
                current_cart_items = list(
                    CartItem.objects.select_for_update()
                    .filter(customer=request.user, listing__pharmacy=pharmacy)
                    .select_related("listing__product", "listing__pharmacy")
                    .order_by("pk")
                )
                if not current_cart_items:
                    raise ValidationError("These cart items have already been checked out or removed.")
                locked_items = []
                for cart_item in current_cart_items:
                    listing = PharmacyListing.objects.select_for_update().select_related("product", "pharmacy").get(pk=cart_item.listing_id)
                    if not listing.active or listing.is_expired or listing.pharmacy.verification_status != Pharmacy.VerificationStatus.APPROVED:
                        raise ValidationError(f"{listing.product.brand_name} is no longer available.")
                    if cart_item.quantity > listing.sellable_quantity:
                        raise ValidationError(f"{listing.product.brand_name} is no longer available in the requested quantity. Please update your cart or contact the pharmacy.")
                    locked_items.append((cart_item, listing))
                needs_prescription = any(listing.product.requires_prescription for _, listing in locked_items)
                prescription = form.cleaned_data.get("prescription")
                if needs_prescription and not prescription:
                    raise ValidationError("This order includes prescription-required medicine. Upload a prescription first.")
                if needs_prescription and prescription.owner_id != request.user.id:
                    raise ValidationError("Select one of your own prescriptions.")
                mode = form.cleaned_data["fulfilment"]
                delivery_fee = pharmacy.delivery_fee if mode == MarketplaceOrder.Fulfilment.DELIVERY else Decimal("0.00")
                subtotal = sum((listing.selling_price * cart_item.quantity for cart_item, listing in locked_items), Decimal("0.00"))
                order = MarketplaceOrder.objects.create(
                    customer=request.user, pharmacy=pharmacy, prescription=prescription,
                    fulfilment=mode, delivery_address=form.cleaned_data.get("delivery_address", "").strip(),
                    customer_note=form.cleaned_data.get("customer_note", "").strip(),
                    subtotal=subtotal, delivery_fee=delivery_fee, total=subtotal + delivery_fee,
                )
                OrderStatusEvent.objects.create(order=order, actor=request.user, old_status="", new_status=order.status, note="Order submitted; stock reserved pending pharmacy review")
                _write_audit(request.user, "order_submitted", order, f"Pharmacy #{pharmacy.pk}; fulfilment={mode}; total={order.total}")
                for cart_item, listing in locked_items:
                    MarketplaceOrderItem.objects.create(
                        order=order, listing=listing, product_name_snapshot=str(listing.product),
                        quantity=cart_item.quantity, unit_price=listing.selling_price, mrp_snapshot=listing.mrp,
                    )
                    listing.reserved_quantity += cart_item.quantity
                    listing.save(update_fields=["reserved_quantity", "last_stock_update", "updated_at"])
                    cart_item.delete()
            messages.success(request, f"Request submitted. Reference: {order.reference}. Your order is pending pharmacy confirmation; it is not yet a completed sale.")
            return redirect("customer_dashboard")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            cart_items = list(CartItem.objects.filter(customer=request.user, listing__pharmacy=pharmacy).select_related("listing__product", "listing__pharmacy"))
            if not cart_items:
                return redirect("cart_detail")
    subtotal = sum((i.subtotal for i in cart_items), Decimal("0.00"))
    return render(request, "marketplace/checkout.html", {"form": form, "pharmacy": pharmacy, "cart_items": cart_items, "subtotal": subtotal})


@login_required
def order_detail(request, reference):
    order = get_object_or_404(MarketplaceOrder.objects.select_related("customer", "pharmacy", "prescription").prefetch_related("items", "status_events"), reference=reference)
    owner_access = _is_pharmacy_owner(request.user, order.pharmacy)
    if order.customer_id != request.user.id and not owner_access:
        raise PermissionDenied
    return render(request, "marketplace/order_detail.html", {"order": order, "owner_access": owner_access})


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def marketplace_admin_dashboard(request):
    context = {
        "customer_count": get_user_model().objects.filter(is_staff=False, is_superuser=False).count(),
        "pharmacy_count": Pharmacy.objects.count(),
        "pending_pharmacies": Pharmacy.objects.filter(verification_status=Pharmacy.VerificationStatus.PENDING).order_by("created_at"),
        "managed_pharmacies": Pharmacy.objects.exclude(verification_status=Pharmacy.VerificationStatus.PENDING).order_by("-updated_at")[:20],
        "verified_pharmacies": Pharmacy.objects.filter(verification_status=Pharmacy.VerificationStatus.APPROVED).count(),
        "medicine_count": MedicineProduct.objects.filter(active=True).count(),
        "listing_count": PharmacyListing.objects.filter(active=True).count(),
        "pending_orders": MarketplaceOrder.objects.filter(status=MarketplaceOrder.Status.PENDING).count(),
        "recent_orders": MarketplaceOrder.objects.select_related("customer", "pharmacy")[:10],
        "recent_audit_events": MarketplaceAuditLog.objects.select_related("actor")[:8],
    }
    return render(request, "marketplace/admin_dashboard.html", context)


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def admin_pharmacy_status(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)
    status = request.POST.get("status", "")
    if status not in {Pharmacy.VerificationStatus.APPROVED, Pharmacy.VerificationStatus.REJECTED, Pharmacy.VerificationStatus.SUSPENDED}:
        messages.error(request, "Choose a valid pharmacy status.")
    else:
        pharmacy.verification_status = status
        pharmacy.verification_note = request.POST.get("note", "")[:240]
        pharmacy.verified_at = timezone.now() if status == Pharmacy.VerificationStatus.APPROVED else None
        pharmacy.save(update_fields=["verification_status", "verification_note", "verified_at", "updated_at"])
        _write_audit(request.user, "pharmacy_status_changed", pharmacy, f"Status={status}; note={pharmacy.verification_note[:100]}")
        messages.success(request, f"{pharmacy.name} status changed to {pharmacy.get_verification_status_display()}.")
    return redirect("marketplace_admin_dashboard")


def content_page(request, slug):
    pages = {
        "about": ("About MedMitra", "A local pharmacy discovery and inventory coordination project.", "MedMitra helps customers discover listed medicines, compare participating pharmacy prices and send order requests. Pharmacy listings appear publicly only after administrator review. Availability is based on retailer-updated data and can change; customers should confirm stock before visiting.\n\nMedMitra is a software marketplace concept, not a medical provider. It does not diagnose, prescribe or replace advice from a qualified healthcare professional."),
        "contact": ("Contact and support", "Questions about an order or a pharmacy listing?", "For an existing order, sign in and open your order details to see its reference and the selected pharmacy. Contact the pharmacy using the contact information shown on its verified profile.\n\nFor account, privacy or platform issues, contact the project administrator using the support channel configured by your deployment owner. This demo does not send SMS or WhatsApp messages unless an external provider is deliberately configured."),
        "privacy": ("Privacy overview", "Sensitive documents and account data should be handled carefully.", "MedMitra stores account data, order request details and private prescription uploads needed for the workflows shown. Prescription downloads are permission-checked in the application and the files are not linked directly from public page templates.\n\nDo not upload real health documents to an unreviewed demo deployment. Before production use, the operator must configure durable private storage, retention and deletion policies, backup protection, access monitoring, applicable privacy notices and required legal reviews."),
        "terms": ("Terms of use", "Please understand what a MedMitra listing represents.", "MedMitra is a pharmacy discovery and order-request interface. A submitted request is not a completed sale and is not a guarantee that a medicine is available. Stock, listed prices, delivery fees and business hours are supplied by participating pharmacies and may change.\n\nThe platform does not recommend medicine substitutes, dosage or self-treatment. Prescription-required products must be reviewed by an appropriately authorized professional before an order can be accepted. Do not use this college-project application for real transactions until applicable pharmacy, drug-sale, privacy, consumer protection, payments and delivery requirements have been reviewed and met."),
    }
    page = pages.get(slug)
    if not page:
        from django.http import Http404
        raise Http404
    return render(request, "marketplace/content_page.html", {"page_title": page[0], "page_intro": page[1], "page_content": page[2]})
