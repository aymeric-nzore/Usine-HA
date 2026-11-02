from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Atelier(models.Model):
    numero = models.CharField(max_length=20, primary_key=True)
    libelle = models.CharField(max_length=120)
    responsable = models.ForeignKey(
        User,
        related_name="ateliers_responsables",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "atelier"
        verbose_name_plural = "ateliers"

    def clean(self):
        if self.responsable_id is None:
            raise ValidationError({"responsable": "Un atelier doit avoir un responsable acteur."})

    def __str__(self):
        return f"{self.numero} — {self.libelle}"


class LigneProduction(models.Model):
    numero = models.CharField(max_length=20, primary_key=True)
    atelier = models.ForeignKey(Atelier, related_name="lignes", on_delete=models.PROTECT)
    operateurs_requis = models.PositiveSmallIntegerField(default=2)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "ligne de production"
        verbose_name_plural = "lignes de production"

    def __str__(self):
        return self.numero


class Produit(models.Model):
    reference = models.CharField(max_length=30, primary_key=True)
    designation = models.CharField(max_length=160)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.reference} — {self.designation}"


class LotProduction(models.Model):
    STATUTS = [("en_cours", "En cours"), ("termine", "Terminé"), ("bloque", "Bloqué")]
    numero_lot = models.CharField(max_length=30, primary_key=True)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    ligne = models.ForeignKey(LigneProduction, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_cours")
    date_debut = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_debut"]
        verbose_name = "lot de production"
        verbose_name_plural = "lots de production"

    def __str__(self):
        return self.numero_lot

# Create your models here.
