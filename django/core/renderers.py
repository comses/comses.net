from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.compat import template_render


class RootContextHTMLRenderer(TemplateHTMLRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders data to HTML, using Django's standard template rendering.

        The template name is determined by (in order of preference):

        1. An explicit .template_name set on the response.
        2. An explicit .template_name set on this class.
        3. The return result of calling view.get_template_names().
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
