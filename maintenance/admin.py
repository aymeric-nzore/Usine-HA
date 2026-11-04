from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Incident, Machine, Maintenance, MaintenancePiece


class MaintenancePieceInline(admin.TabularInline):
    model = MaintenancePiece
    extra = 0
    autocomplete_fields = ("piece",)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("identifiant", "nom", "ligne", "etat")
    list_filter = ("etat", "ligne")
    search_fields = ("identifiant", "nom")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "typologie", "lot", "statut", "arret_minutes", "created_at")
    list_filter = ("statut", "typologie")
    search_fields = ("description", "typologie")


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ("machine", "description", "debut", "duree_minutes", "preventive")
    list_filter = ("preventive", "machine")
    search_fields = ("machine__identifiant", "machine__nom", "description")
    inlines = (MaintenancePieceInline,)


@admin.register(MaintenancePiece)
class MaintenancePieceAdmin(admin.ModelAdmin):
    list_display = ("maintenance", "piece", "quantite")
    list_filter = ("maintenance", "piece")
    search_fields = ("piece__reference", "piece__libelle")
    autocomplete_fields = ("maintenance", "piece")
