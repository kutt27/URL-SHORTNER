from django import forms
from django.core.exceptions import ValidationError
from shortener.models import URLShortener
from shortener.utils import is_valid_custom_alias

class UrlForm(forms.Form):
    link = forms.URLField(
        max_length=2048,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': '🔗 Enter your long URL here (e.g., https://example.com/very/long/path)',
            'id': 'url-input',
            'autocomplete': 'url',
            'spellcheck': 'false',
            'required': True
        }),
        help_text="Enter the URL you want to shorten"
    )

    custom_alias = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '✨ Custom alias (optional, e.g., my-link)',
            'id': 'custom-alias-input',
            'pattern': '[a-zA-Z0-9_-]+',
            'title': 'Only letters, numbers, hyphens, and underscores allowed'
        }),
        help_text="Optional: Create a custom alias for your short URL"
    )

    def clean_custom_alias(self):
        alias = self.cleaned_data.get('custom_alias')

        if alias:
            # Validate format
            if not is_valid_custom_alias(alias):
                raise ValidationError(
                    "Custom alias must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores. "
                    "Reserved words are not allowed."
                )

            # Check if alias already exists
            if URLShortener.objects.filter(custom_alias=alias, is_active=True).exists():
                raise ValidationError("This custom alias is already taken. Please choose another one.")

            # Check if it conflicts with short codes
            if URLShortener.objects.filter(short_code=alias, is_active=True).exists():
                raise ValidationError("This alias conflicts with an existing short code. Please choose another one.")

        return alias

    def clean_link(self):
        link = self.cleaned_data.get('link')

        if link:
            # Basic URL validation is handled by URLField
            # Additional custom validation can be added here
            if len(link) > 2048:
                raise ValidationError("URL is too long. Maximum length is 2048 characters.")

        return link