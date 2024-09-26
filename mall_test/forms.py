from django import forms
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        # fields = '__all__' # FIXME 테스트로 모든 필드 입력받기 일단은
        fields = ["name", "amount"]
