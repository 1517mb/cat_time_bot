import logging
import secrets
import string

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.http import require_POST

from .forms import PasswordGeneratorForm

logger = logging.getLogger(__name__)


def index(request):
    initial_data = {
        "length": 12,
        "include_digits": True,
        "include_special_chars": False,
    }
    form = PasswordGeneratorForm(initial=initial_data)
    return render(request, "index.html", {"form": form})


def generate_password(request):
    try:
        if request.method == "POST":
            form = PasswordGeneratorForm(request.POST)
            if form.is_valid():
                length = form.cleaned_data["length"]
                include_digits = form.cleaned_data["include_digits"]
                include_special_chars = form.cleaned_data[
                    "include_special_chars"]

                characters = string.ascii_letters
                if include_digits:
                    characters += string.digits
                if include_special_chars:
                    characters += string.punctuation

                password = "".join(
                    secrets.choice(characters) for _ in range(length))
                return render(request,
                              "password_partial.html", {"password": password})
            logger.warning("Неверные данные формы: %s", form.errors)
            return render(request, "form_errors_partial.html", {"form": form})
        logger.warning("Недопустимый метод запроса: %s", request.method)
        return HttpResponse("Метод, который не разрешен", status=405)
    except Exception as e:
        logger.error("Ошибка при генерации пароля: %s", str(e))
        return HttpResponse("Внутренняя ошибка сервера", status=500)


def copy_password(request):
    return JsonResponse({"status": "ok"})


@require_POST
def generate_password_view(request):
    password = generate_password()
    template = loader.get_template("password_partial.html")
    return HttpResponse(template.render({"password": password}))


def tips(request):
    initial_data = {
        "length": 12,
        "include_digits": True,
        "include_special_chars": False,
    }
    form = PasswordGeneratorForm(initial=initial_data)
    return render(request, "index.html", {"form": form})
