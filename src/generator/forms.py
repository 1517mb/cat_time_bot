from django import forms


class PasswordGeneratorForm(forms.Form):
    length = forms.IntegerField(initial=12, min_value=8, max_value=50)
    include_digits = forms.BooleanField(required=False)
    include_special_chars = forms.BooleanField(required=False)
