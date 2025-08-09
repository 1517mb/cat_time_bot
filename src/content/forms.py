from django import forms


class RatingForm(forms.Form):
    RATING_CHOICES = [
        (1, "1 звезда"),
        (2, "2 звезды"),
        (3, "3 звезды"),
        (4, "4 звезды"),
        (5, "5 звёзд")
    ]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect,
        label="Ваша оценка"
    )


class ProgramFilterForm(forms.Form):
    SEARCH_CHOICES = [
        ("name", "По названию"),
        ("description", "По описанию"),
        ("all", "Везде")
    ]

    SORT_CHOICES = [
        ("-created_at", "Новизне"),
        ("-downloads", "Популярности"),
        ("-rating", "Рейтингу")
    ]

    search = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={
            "class": "input is-fullwidth",
            "placeholder": "Поиск..."
        })
    )

    search_in = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        initial="all",
        label="",
        widget=forms.Select(attrs={
            "class": "select is-fullwidth"
        })
    )

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        initial="-created_at",
        label="",
        widget=forms.Select(attrs={
            "class": "select is-fullwidth"
        })
    )

    min_rating = forms.DecimalField(
        required=False,
        max_digits=3,
        decimal_places=2,
        label="",
        widget=forms.NumberInput(attrs={
            "class": "input is-fullwidth",
            "placeholder": "Мин. рейтинг",
            "min": "0",
            "max": "5",
            "step": "0.1"
        })
    )
