from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from production.models import Atelier
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        related_name="profile",
        on_delete=models.CASCADE,
    )
    matricule = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Matricule employé (généré automatiquement, préfixe UsineHA-).",
    )
    atelier = models.ForeignKey(
        Atelier,
        related_name="membres",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def clean(self):
        if self.user_id and not self.user.is_staff and self.atelier_id is None:
            raise ValidationError({"atelier": "Un utilisateur métier doit avoir un atelier."})


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Equipe(models.Model):
    numero = models.CharField(max_length=20, primary_key=True)
    designation = models.CharField(max_length=120)
    responsable = models.ForeignKey(User, on_delete=models.PROTECT)
    atelier = models.ForeignKey(
        Atelier,
        related_name="equipes",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("responsable",),
                name="unique_responsable_equipe",
            ),
        ]

    def __str__(self):
        return f"{self.numero} — {self.designation}"

    def clean(self):
        if self.atelier_id is None:
            raise ValidationError({"atelier": "Une équipe doit être rattachée à un atelier."})


class Operateur(models.Model):
    matricule = models.CharField(max_length=30, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    equipe = models.ForeignKey(Equipe, related_name="operateurs", on_delete=models.PROTECT)
    date_embauche = models.DateField()

    def __str__(self):
        return self.user.get_full_name() or self.user.username

# Create your models here.
