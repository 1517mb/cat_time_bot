from django import forms


class PasswordGeneratorForm(forms.Form):
    length = forms.IntegerField(
        initial=12,
        min_value=8,
        max_value=50,
        widget=forms.NumberInput(attrs={
            "class": "input",
            "id": "length",
        }),
    )
    include_digits = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            "class": "checkbox",
            "id": "include_digits",
        }),
    )
    include_special_chars = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "checkbox",
            "id": "include_special_chars",
        }),
    )
