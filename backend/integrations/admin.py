from django.contrib import admin

from .models import Integration, Bot

# Register your models here.
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ["thirdparty", "is_chat_app", "is_active", "created_at"]
    list_filter = ["is_chat_app", "is_active"]


class BotAdmin(admin.ModelAdmin):
    list_display = ["agent", "user_token_expires_at", "created_at"]


admin.site.register(Integration, IntegrationAdmin)
admin.site.register(Bot, BotAdmin)