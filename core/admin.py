# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Project, Customer, Assignment, Photo


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username', 'code', 'first_name', 'last_name',
        'company', 'district', 'team', 'group',
    )
    search_fields = ('username', 'code', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('所属情報', {
            'fields': ('code', 'company', 'district', 'team', 'group'),
        }),
    )


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1
    readonly_fields = ('sequence', 'performed_at', 'checked_at')
    autocomplete_fields = (
        'customer',
        'performed_by',
        'checked_by',
    )
    fields = (
        'sequence',
        'customer',
        'pr_status',
        'open_round',
        'open_status',
        'performed_by',
        'performed_at',
        'checked_by',
        'checked_at',
        'gauge_spec',
        'absence_action',
        'leaflet_type',
        'leaflet_status',
        'm_valve_state',
        'm_valve_attach',
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')
    search_fields = ('name',)
    filter_horizontal = ('allowed_users',)
    inlines = (AssignmentInline,)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('usage_no', 'room_number', 'name', 'building_name')
    search_fields = ('usage_no', 'name', 'room_number')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'project',
        'sequence',
        'customer',
        'pr_status',
        'open_round',
        'open_status',
        'performed_by',
        'checked_by',
    )
    list_filter = (
        'project',
        'pr_status',
        'open_round',
        'open_status',
        'gauge_spec',
        'leaflet_type',
    )
    search_fields = ('customer__usage_no', 'customer__name')
    autocomplete_fields = (
        'project',
        'customer',
        'performed_by',
        'checked_by',
    )
    # ↓ この行を削除しました
    # inlines = (AssignmentInline,)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'photo_type', 'timestamp')
    autocomplete_fields = ('assignment',)
