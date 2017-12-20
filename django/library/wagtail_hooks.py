from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from library import models


class CodebaseImageAdmin(ModelAdmin):
    model = models.CodebaseImage
    list_display = ('title', 'file',)
    search_fields = ('title',)

modeladmin_register(CodebaseImageAdmin)