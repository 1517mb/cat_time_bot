from django.shortcuts import render
from .forms import PasswordGeneratorForm


def home(request):
    form = PasswordGeneratorForm()
    return render(request, "index.html", {"form": form})
