from django.db import models
from production.models import LigneProduction, LotProduction
from stock.models import Piece


class Machine(models.Model):
    identifiant = models.CharField(max_length=30, primary_key=True)
    ligne = models.ForeignKey(LigneProduction, related_name="machines", on_delete=models.PROTECT)
    nom = models.CharField(max_length=120)
    ETATS = [("operationnelle", "Opérationnelle"), ("maintenance", "Maintenance"), ("arret", "À l'arrêt")]
    etat = models.CharField(max_length=20, choices=ETATS, default="operationnelle")

    def __str__(self):
        return f"{self.identifiant} — {self.nom}"


class Incident(models.Model):
    STATUTS = [("ouvert", "Ouvert"), ("en_cours", "En cours"), ("resolu", "Résolu")]
    numero_incident = models.AutoField(primary_key=True)
    lot = models.ForeignKey(LotProduction, related_name="incidents", on_delete=models.PROTECT)
    typologie = models.CharField(max_length=80)
    description = models.TextField()
    arret_minutes = models.PositiveIntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUTS, default="ouvert")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "incident"
        verbose_name_plural = "incidents"

    def __str__(self):
        return f"INC-{self.numero_incident:04d}"


class Maintenance(models.Model):
    machine = models.ForeignKey(Machine, related_name="maintenances", on_delete=models.PROTECT)
    description = models.CharField(max_length=180)
    debut = models.DateTimeField()
    duree_minutes = models.PositiveIntegerField(default=60)
    preventive = models.BooleanField(default=False)

    class Meta:
        ordering = ["-debut"]

    def pieces_utilisees(self):
        """Retourne les pièces utilisées avec leur quantité pour cette maintenance."""
        return self.maintenance_pieces.select_related("piece").all()


class MaintenancePiece(models.Model):
    """Pièce consommée lors d'une intervention de maintenance."""
    maintenance = models.ForeignKey(
        Maintenance,
        related_name="maintenance_pieces",
        on_delete=models.CASCADE,
    )
    piece = models.ForeignKey(
        Piece,
        related_name="utilisee_dans_maintenances",
        on_delete=models.PROTECT,
    )
    quantite = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("maintenance", "piece")
        verbose_name = "pièce utilisée"
        verbose_name_plural = "pièces utilisées"

    def __str__(self):
        return f"{self.piece.reference} × {self.quantite} (maintenance {self.maintenance.pk})"

# Create your models here.
