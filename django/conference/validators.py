from django.core.validators import MinLengthValidator


class MarkdownMinLengthValidator(MinLengthValidator):
    def clean(self, x):
        return len(x.raw)