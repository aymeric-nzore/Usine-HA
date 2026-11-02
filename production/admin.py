from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Atelier, LigneProduction, Produit, LotProduction


@admin.register(Atelier)
class AtelierAdmin(admin.ModelAdmin):
    list_display = ("numero", "libelle", "responsable", "actif")
    search_fields = ("numero", "libelle", "responsable__username", "responsable__last_name")
    list_filter = ("actif",)
    autocomplete_fields = ("responsable",)


@admin.register(LigneProduction)
class LigneProductionAdmin(admin.ModelAdmin):
    list_display = ("numero", "atelier", "operateurs_requis", "actif")
    list_filter = ("atelier", "actif")


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ("reference", "designation", "quantite_stock", "prix_unitaire")
    search_fields = ("reference", "designation")


@admin.register(LotProduction)
class LotProductionAdmin(admin.ModelAdmin):
    list_display = ("numero_lot", "produit", "ligne", "quantite", "statut", "date_debut")
    list_filter = ("statut", "ligne")
    search_fields = ("numero_lot", "produit__reference")
