from django.contrib import admin

from .models import Integration

# Register your models here.
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ["thirdparty", "is_chat_app", "created_at"]
    list_filter = ["is_chat_app"]


admin.site.register(Integration, IntegrationAdmin)
