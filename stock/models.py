from django.db import models
from production.models import Atelier
from django.core.exceptions import ValidationError


class Piece(models.Model):
    reference = models.CharField(max_length=30, primary_key=True)
    libelle = models.CharField(max_length=160)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_stock = models.PositiveIntegerField(default=0)
    seuil_alerte = models.PositiveIntegerField(default=10)
    atelier = models.ForeignKey(
        Atelier,
        related_name="pieces",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.reference} — {self.libelle}"

    def clean(self):
        if self.atelier_id is None:
            raise ValidationError({"atelier": "Une pièce doit être rattachée à un atelier."})


class NomenclaturePiece(models.Model):
    piece_parente = models.ForeignKey(Piece, related_name="composants", on_delete=models.CASCADE)
    composant = models.ForeignKey(Piece, related_name="utilise_dans", on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("piece_parente", "composant")


class Fournisseur(models.Model):
    code_fournisseur = models.CharField(max_length=30, primary_key=True)
    raison_sociale = models.CharField(max_length=160)
    telephone = models.CharField(max_length=30)
    adresse = models.TextField()

    def __str__(self):
        return self.raison_sociale


class AchatPiece(models.Model):
    piece = models.ForeignKey(Piece, on_delete=models.PROTECT)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.PositiveIntegerField()
    date_transaction = models.DateField(auto_now_add=True)

# Create your models here.
