import uuid
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.models import StaffProfile
from .models import Medicine, StockMovement, MedicineSale, MedicineSaleItem
from .forms import MedicineForm

def _allowed(user, roles=None):
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, 'staff_profile', None)
    return bool(profile and profile.is_approved and profile.role in {StaffProfile.Role.PHARMACIST, StaffProfile.Role.STORE_MANAGER} and (roles is None or profile.role in roles))

def _require(user, roles=None):
    if not _allowed(user, roles): raise PermissionDenied

@login_required
def dashboard(request):
    _require(request.user, [StaffProfile.Role.PHARMACIST, StaffProfile.Role.STORE_MANAGER])
    today = timezone.localdate()
    meds = Medicine.objects.filter(active=True)
    low_stock = list(meds.filter(quantity__lte=F('minimum_stock')).order_by('quantity', 'name'))
    restock_suggestions = [
        {"medicine": med, "suggested_quantity": max(med.minimum_stock * 2 - med.quantity, med.minimum_stock, 1)}
        for med in low_stock
    ]
    context = {
        "medicine_count": meds.count(),
        "low_stock": low_stock,
        "restock_suggestions": restock_suggestions,
        "near_expiry": meds.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=60)).order_by('expiry_date')[:30],
        "expired_medicines": meds.filter(expiry_date__lt=today).order_by('expiry_date')[:30],
        "out_of_stock_count": meds.filter(quantity=0).count(),
        "today_sales": MedicineSale.objects.filter(created_at__date=today).aggregate(total=Sum('total'))['total'] or 0,
        "recent_sales": MedicineSale.objects.select_related('created_by')[:8],
    }
    return render(request, 'pharmacy/dashboard.html', context)

@login_required
def medicine_list(request):
    _require(request.user,[StaffProfile.Role.PHARMACIST,StaffProfile.Role.STORE_MANAGER])
    query=request.GET.get('q','').strip()
    medicines=Medicine.objects.all()
    if query: medicines=medicines.filter(name__icontains=query) | medicines.filter(generic_name__icontains=query)
    return render(request,'pharmacy/medicines.html',{'medicines':medicines,'query':query})

@login_required
def medicine_add(request):
    _require(request.user,[StaffProfile.Role.PHARMACIST,StaffProfile.Role.STORE_MANAGER])
    form=MedicineForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            med=form.save()
            if med.quantity: StockMovement.objects.create(medicine=med,user=request.user,change=med.quantity,reason='Opening stock')
        messages.success(request,'Medicine saved to inventory.')
        return redirect('pharmacy_medicines')
    return render(request,'pharmacy/medicine_form.html',{'form':form,'heading':'Add medicine'})

@login_required
def medicine_edit(request,pk):
    _require(request.user,[StaffProfile.Role.PHARMACIST,StaffProfile.Role.STORE_MANAGER])
    medicine=get_object_or_404(Medicine,pk=pk)
    form=MedicineForm(request.POST or None,instance=medicine)
    if request.method=='POST' and form.is_valid():
        old=medicine.quantity
        with transaction.atomic():
            med=form.save()
            if med.quantity != old: StockMovement.objects.create(medicine=med,user=request.user,change=med.quantity-old,reason='Manual stock correction')
        messages.success(request,'Medicine updated.')
        return redirect('pharmacy_medicines')
    return render(request,'pharmacy/medicine_form.html',{'form':form,'heading':'Edit medicine'})

@login_required
def stock_movement_list(request):
    _require(request.user,[StaffProfile.Role.PHARMACIST,StaffProfile.Role.STORE_MANAGER])
    return render(request,'pharmacy/stock.html',{'movements':StockMovement.objects.select_related('medicine','user')[:100]})

@login_required
def sale_create(request):
    _require(request.user,[StaffProfile.Role.PHARMACIST,StaffProfile.Role.STORE_MANAGER])
    if request.method=='POST':
        med=get_object_or_404(Medicine,pk=request.POST.get('medicine'),active=True)
        try: qty=int(request.POST.get('quantity','0'))
        except ValueError: qty=0
        if qty < 1 or qty > med.quantity or med.expired:
            messages.error(request,'Enter a valid quantity. Expired medicines or quantities above available stock cannot be sold.')
            return redirect('pharmacy_sale')
        with transaction.atomic():
            med=Medicine.objects.select_for_update().get(pk=med.pk)
            if qty > med.quantity or med.expired:
                messages.error(request,'Stock changed or medicine expired. Please retry.')
                return redirect('pharmacy_sale')
            sale=MedicineSale.objects.create(patient_name=request.POST.get('patient_name','')[:160],receipt_number='MC-'+uuid.uuid4().hex[:10].upper(),created_by=request.user,payment_method=request.POST.get('payment_method','cash'))
            MedicineSaleItem.objects.create(sale=sale,medicine=med,quantity=qty,unit_price=med.selling_price)
            sale.total=med.selling_price*qty; sale.save(update_fields=['total'])
            med.quantity-=qty; med.save(update_fields=['quantity'])
            StockMovement.objects.create(medicine=med,user=request.user,change=-qty,reason=f'Sale {sale.receipt_number}')
        messages.success(request,f'Sale recorded. Receipt {sale.receipt_number}.')
        return redirect('pharmacy_dashboard')
    return render(request,'pharmacy/sale.html',{'medicines':Medicine.objects.filter(active=True,quantity__gt=0,expiry_date__gte=timezone.localdate()) | Medicine.objects.filter(active=True,quantity__gt=0,expiry_date__isnull=True)})
