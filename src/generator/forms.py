import string

from django import forms

PASSWORD_CHARSETS = {
    "letters": string.ascii_letters,
    "digits": string.digits,
    "special": string.punctuation,
}


class PasswordGeneratorForm(forms.Form):
    length = forms.IntegerField(
        initial=12,
        min_value=8,
        max_value=64,
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
    include_hyphen = forms.BooleanField(
        required=False,
        initial=True,
        label="Включить дефис (-)",
        widget=forms.CheckboxInput(attrs={
            "class": "checkbox",
            "id": "include_hyphen",
        }),
    )
    include_underscore = forms.BooleanField(
        required=False,
        initial=False,
        label="Включить подчеркивание (_)",
        widget=forms.CheckboxInput(attrs={
            "class": "checkbox",
            "id": "include_underscore",
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        length = cleaned_data.get("length")
        include_hyphen = cleaned_data.get("include_hyphen")
        include_underscore = cleaned_data.get("include_underscore")

        if length is None:
            return cleaned_data
        req_separators_count = 0
        if include_hyphen:
            req_separators_count += 1
        if include_underscore:
            req_separators_count += 1

        min_req_len = req_separators_count * 2

        if length < min_req_len:
            self.add_error(
                "length",
                f"Для выбранных разделителей длина должна быть не менее "
                f"{min_req_len} символов."
            )

        if length < 8:
            self.add_error(
                "length", "Минимальная длина пароля - 8 символа."
            )

        return cleaned_data


class IpLookupForm(forms.Form):
    host = forms.CharField(
        label="IP адрес или домен",
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input is-medium",
            "placeholder": "Например: 8.8.8.8 или google.com"
        })
    )
