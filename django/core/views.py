from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from . import summarization


@api_view(['POST'], exclude_from_schema=True)
@permission_classes([])
def summarize_text(request):
    return Response(summarization.summarize_to_text(request.data['description'], 2))


class AddEditFormViewSetMixin(object):

    """
    Provide routing and template discovery conventions for ViewSets that need to render forms. These could also just be
    explicit in urls.py but this helps to keep them in one place.


    Override 'namespace' property to set the namespace directly, e.g.,

    namespace = 'library/codebases'

    By default the namespace will be set to <app-label>/<model-name> which is typically not pluralized. This namespace
    is used for the URL namespace as well as the template filesystem namespace, where the template files are discovered.
    """

    ACTIONS = ('list', 'retrieve', 'add', 'edit', 'delete')

    @renderer_classes((TemplateHTMLRenderer,))
    def edit(self, request, **kwargs):
        self.object = self.get_object()
        return Response({'object': self.object})

    def add(self, request, **kwargs):
        # FIXME: need to add an appropriate AnonymousUser check via django-guardian. Normal IsAuthenticated permissions
        # won't work otherwise since AnonymousUser is considered 'authenticated' for some reason.
        return Response({})

    def _get_namespace(self):
        namespace = getattr(self, 'namespace', None)
        if namespace is None:
            meta = self.get_queryset().model._meta
            app_label = meta.app_label
            namespace = '{0}/{1}'.format(app_label, meta.verbose_name_plural.replace(' ', '_'))
            self.namespace = namespace
        return namespace

    def get_template_names(self):
        # default to the lowercased model name
        namespace = self._get_namespace()
        file_ext = getattr(self, 'ext', 'jinja')
        templates = {}
        for action in self.ACTIONS:
            # by convention, templates will be named <action>.<file-ext> and discovered in the template filesystem under
            # `django/<app-name>/templates/<namespace>/<action>.<file-ext>`
            template_name = '{0}.{1}'.format(action, file_ext)
            templates[action] = ['{0}/{1}'.format(namespace, template_name), template_name]
        if self.action in templates.keys():
            return templates[self.action]
        # FIXME: is this an appropriate default or should we return a 404?
        return ['rest_framework/api.html']
