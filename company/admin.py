# companies/admin.py (or users/admin.py if defined there)
from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "rc_number", "website", "type")
    search_fields = ("name", "rc_number")
    list_filter = ("type",)
