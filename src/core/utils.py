import uuid
from django.utils.text import slugify


def cyrillic_slugify(s):
    """Транслитерация + обработка пустых значений"""
    translit_map = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
    }
    transliterated = "".join(translit_map.get(c.lower(), c) for c in str(s))
    slug = slugify(transliterated)
    return slug or f"untitled-{uuid.uuid4().hex[:6]}"
