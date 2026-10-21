from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class Medicine(models.Model):
    name = models.CharField(max_length=160, db_index=True)
    generic_name = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=100, blank=True)
    strength = models.CharField(max_length=80, blank=True)
    batch_number = models.CharField(max_length=80, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=10)
    requires_prescription = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['name']
    def __str__(self): return f'{self.name} ({self.strength})' if self.strength else self.name
    @property
    def low_stock(self): return self.quantity <= self.minimum_stock
    @property
    def expired(self): return bool(self.expiry_date and self.expiry_date < timezone.localdate())

class StockMovement(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='movements')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    change = models.IntegerField()
    reason = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class MedicineSale(models.Model):
    patient_name = models.CharField("Customer name", max_length=160, blank=True)
    receipt_number = models.CharField(max_length=24, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=[('cash','Cash'),('upi','UPI'),('card','Card')], default='cash')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class MedicineSaleItem(models.Model):
    sale = models.ForeignKey(MedicineSale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    @property
    def subtotal(self): return self.quantity * self.unit_price
