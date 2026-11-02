from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AchatPiece, Fournisseur, NomenclaturePiece, Piece

@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ("reference", "libelle", "atelier", "quantite_stock", "seuil_alerte")
    list_filter = ("atelier",)
    search_fields = ("reference", "libelle")


admin.site.register(NomenclaturePiece)
admin.site.register(Fournisseur)
admin.site.register(AchatPiece)
