from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import PendingTagCleanup


class PendingTagCleanupAdmin(ModelAdmin):
    model = PendingTagCleanup
    list_display = ('old_name', 'new_name', 'transaction_id',)
    list_filter = ('is_active',)
    search_fields = ('old_name', 'new_name',)
    ordering = ('id',)


modeladmin_register(PendingTagCleanupAdmin)
