from django import forms
from .models import Medicine
class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name','generic_name','category','strength','batch_number','expiry_date','purchase_price','selling_price','quantity','minimum_stock','requires_prescription','active']
        widgets = {'expiry_date': forms.DateInput(attrs={'type':'date','class':'form-control'}), 'requires_prescription': forms.CheckboxInput(attrs={'class':'form-check-input'}), 'active': forms.CheckboxInput(attrs={'class':'form-check-input'})}
        formlabels = None
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name, field in self.fields.items():
            if name not in ('requires_prescription','active','expiry_date'):
                field.widget.attrs['class'] = 'form-control'
