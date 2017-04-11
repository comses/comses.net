from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.compat import template_render


class RootContextHTMLRenderer(TemplateHTMLRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Same as TemplateHTMLRenderer but adds a root __all__ variable that contains the entire serialized object
        """
        renderer_context = renderer_context or {}
        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        if response.exception:
            template = self.get_exception_template(response)
        else:
            template_names = self.get_template_names(response, view)
            template = self.resolve_template(template_names)

        if hasattr(self, 'resolve_context'):
            # Fallback for older versions.
            context = self.resolve_context(data, request, response)
        else:
            context = self.get_template_context(data, renderer_context)

        context['__all__'] = data
        return template_render(template, context, request=request)
