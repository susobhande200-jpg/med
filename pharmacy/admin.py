from django.contrib import admin
from .models import Medicine, StockMovement, MedicineSale, MedicineSaleItem
@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display=('name','category','batch_number','expiry_date','quantity','minimum_stock','selling_price','active')
    list_filter=('category','active','requires_prescription')
    search_fields=('name','generic_name','batch_number')
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin): list_display=('medicine','change','reason','user','created_at'); readonly_fields=('medicine','change','reason','user','created_at')
class SaleItemInline(admin.TabularInline): model=MedicineSaleItem; extra=0
@admin.register(MedicineSale)
class MedicineSaleAdmin(admin.ModelAdmin): list_display=('receipt_number','patient_name','total','payment_method','created_by','created_at'); inlines=[SaleItemInline]; readonly_fields=('receipt_number','created_by','total','created_at')
