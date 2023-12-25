from django import forms
from django.forms import ModelForm
from salesMonitor.models import FbaShipmentCost

class UploadFilesForm(forms.Form):
    file_field = forms.FileField(label='上传货件明细文件，可一次上传多个',widget=forms.ClearableFileInput(attrs={'multiple': True}))

class UploadFileForm(forms.Form):
    file = forms.FileField()

class UploadFileCountryForm(forms.Form):
    COUNTRIES = (('US','US'), ('EU', 'EU'), ('GB', 'GB'), ('CA', 'CA'), ('JP', 'JP'), ('AU', 'AU'),)
    file = forms.FileField(required=False)
    country = forms.ChoiceField(choices=COUNTRIES)


class UploadShipmentFileForm(ModelForm):
    class Meta:
        model = FbaShipmentCost
        fields = ['shipment_id', 'shipway', 'cost_per_kg']
    file = forms.FileField(label='上传货件明细文件，一次一个文件，上传前需要确认Sku重量信息已经上传')

class AsinForm(forms.Form):
    asin = forms.CharField()

class SkuForm(forms.Form):
    sku = forms.CharField()

class UploadTransactionAdCurrencyForm(forms.Form):
    import datetime
    start_date = forms.DateField(initial=datetime.date.today)
    end_date = forms.DateField(initial=datetime.date.today)
    file1 = forms.FileField(label='亚马逊Payment交易报告')
    file2 = forms.FileField(label='亚马逊产品广告交易报告',required=False)
    file3 = forms.FileField(label='亚马逊品牌广告交易报告',required=False)
    file4 = forms.FileField(label='汇率')

class ConfirmPoHeadShippingForm(forms.Form):
    CHOICES = [('yes', '确认'), ('no', '需要修改')]
    yes_or_no = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES, initial = ('no', '需要修改'))

class FcCodeCountryForm(forms.Form):
    fc_code = forms.CharField()
    FC_COUNTRIES = (('US','US'), ('EU', 'EU'), ('GB', 'GB'),('JP', 'JP'),('AE', 'AE'), ('SA','SA'),('CA','CA'),('AU', 'AU'),)
    country = forms.ChoiceField(widget=forms.RadioSelect, choices=FC_COUNTRIES, initial = ('US', 'US'))
