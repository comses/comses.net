from django import forms
from wagtail.utils.widgets import WidgetWithScript


class MarkdownTextarea(WidgetWithScript, forms.widgets.Textarea):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def render_js_init(self, domId, name, value):
        return 'simplemdeAttach("{0}");'.format(domId)

    def render(self, name, value, attrs=None, renderer=None):
        # The raw content of markupfield needs to extracted for the MarkDown to display properly
        if hasattr(value, 'raw'):
            value = value.raw
        # renderer isn't passed here because WidgetWithScript doesn't have that argument
        return super().render(name, value, attrs)

    class Media:
        css = {
            'all': (
                # FIXME: this hardcoded URL should instead be pulled from frontend simplemde dependencies
                'https://cdnjs.cloudflare.com/ajax/libs/simplemde/1.11.2/simplemde.min.css',
            )
        }
        js = (
            # FIXME: this hardcoded URL should be instead be pulled from frontend simplemde dependencies
            'https://cdnjs.cloudflare.com/ajax/libs/simplemde/1.11.2/simplemde.min.js',
            'js/simplemde.attach.js',
        )
