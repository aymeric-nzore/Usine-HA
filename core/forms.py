from django import forms
from django.contrib.auth.forms import AuthenticationForm

from maintenance.models import Incident, Maintenance
from production.models import Atelier
from stock.models import Piece


def available_ateliers(user):
    profile_atelier = getattr(getattr(user, "profile", None), "atelier", None)
    if profile_atelier is None:
        return Atelier.objects.none()
    return Atelier.objects.filter(pk=profile_atelier.pk, actif=True)


class TeamLoginForm(AuthenticationForm):
    atelier = forms.ModelChoiceField(
        label="Atelier",
        queryset=Atelier.objects.filter(actif=True),
        empty_label="Choisir votre atelier",
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        atelier = cleaned_data.get("atelier")
        if user and not user.is_staff:
            if atelier is None:
                self.add_error("atelier", "Sélectionnez votre atelier pour continuer.")
            elif not available_ateliers(user).filter(pk=atelier.pk).exists():
                self.add_error(
                    "atelier",
                    "Cet atelier ne vous est pas attribué.",
                )
        return cleaned_data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff:
            raise forms.ValidationError(
                "Les administrateurs se connectent depuis l’administration Django.",
                code="staff_login_restricted",
            )


class AtelierSelectionForm(forms.Form):
    atelier = forms.ModelChoiceField(
        label="Atelier de travail",
        queryset=Atelier.objects.none(),
        empty_label=None,
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["atelier"].queryset = available_ateliers(user)


class IncidentForm(forms.ModelForm):
    def __init__(self, atelier, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lot"].queryset = self.fields["lot"].queryset.filter(
            ligne__atelier=atelier
        )

    class Meta:
        model = Incident
        fields = ("lot", "typologie", "description", "arret_minutes", "statut")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class PieceForm(forms.ModelForm):
    def __init__(self, atelier, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.atelier = atelier
        self.instance.atelier = atelier

    def save(self, commit=True):
        piece = super().save(commit=False)
        piece.atelier = self.atelier
        if commit:
            piece.save()
        return piece

    class Meta:
        model = Piece
        fields = ("reference", "libelle", "prix_unitaire", "quantite_stock", "seuil_alerte")


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ("machine", "description", "debut", "duree_minutes", "preventive")
        widgets = {
            "debut": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, atelier, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["machine"].queryset = self.fields["machine"].queryset.filter(
            ligne__atelier=atelier
        )
        self.fields["debut"].input_formats = ["%Y-%m-%dT%H:%M"]
