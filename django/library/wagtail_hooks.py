from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register)

from .models import CodebaseImage


class CodebaseImageAdmin(ModelAdmin):
    model = CodebaseImage
    list_display = ('title', 'file',)
    search_fields = ('title',)


modeladmin_register(CodebaseImageAdmin)
