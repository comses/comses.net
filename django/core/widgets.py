from wagtailmarkdown import widgets


class MarkdownTextarea(widgets.MarkdownTextarea):

    def render(self, name, value, attrs=None, renderer=None):
        # The raw content of markupfield needs to extracted for the MarkDown to display properly
        if hasattr(value, 'raw'):
            value = value.raw
        # renderer isn't passed here because WidgetWithScript doesn't have that argument
        return super().render(name, value, attrs)


