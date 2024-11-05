import secrets
import string
from django_unicorn.components import UnicornView


class PasswordGeneratorView(UnicornView):
    password: str = ""
    password_options: list = []
    length: int = 12
    include_digits: bool = True
    include_special_chars: bool = True

    def generate_password(self) -> None:
        """
        Generates the main password and a list of password options based on
        the selected criteria: length, inclusion of digits,
        and special characters.

        :param self: The PasswordGeneratorView instance
        :type self: PasswordGeneratorView

        The generated passwords are stored in the `password` and
        `password_options` attributes.
        """
        custom_ascii_letters = ''.join(
            [char for char in string.ascii_letters if char not in ('I', 'l')])
        characters: str = custom_ascii_letters
        if self.include_digits:
            characters += string.digits
        if self.include_special_chars:
            characters += string.punctuation

        self.length = min(self.length, 50)
        self.length = max(self.length, 8)

        # Generate the main password
        self.password: str = "".join(
            secrets.choice(characters) for _ in range(self.length))

        # Generate a list of password options
        self.password_options: list[str] = [
            "".join(secrets.choice(characters) for _ in range(self.length))
            for _ in range(10)
        ]

    def copy_to_clipboard(self, text: str) -> None:
        """
        Copies the given text to the user's clipboard using the
        `copyToClipboard` function from the `clip.js` script.

        :param text: The text to copy to the user's clipboard
        """
        # Call the `copyToClipboard` function from the `clip.js` script
        # with the given text as the argument
        self.call("copyToClipboard", text)
