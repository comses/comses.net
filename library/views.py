from django.shortcuts import render
from rest_framework import generics, viewsets

from .models import Codebase

class CodeViewSet(viewsets.ModelViewSet):
    queryset = Codebase.objects.all()
    serializer_class = CodeSerializer
    pagination_class = SmallResultSetPagination
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer,)

    @property
    def template_name(self):
        return 'home/model/{}.html'.format(self.action)
