from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django import forms
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models
from production.models import Atelier

from .models import Equipe, Operateur, UserProfile


admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    can_delete = False
    autocomplete_fields = ("atelier",)
    fields = ("matricule", "atelier")
    readonly_fields = ("matricule",)


class AdminUserCreationForm(UserCreationForm):
    groups = forms.ModelMultipleChoiceField(
        label="Rôle(s)",
        queryset=Group.objects.none(),
        required=True,
        help_text="Le rôle détermine les fonctionnalités accessibles.",
    )
    atelier = forms.ModelChoiceField(
        label="Atelier d’appartenance",
        queryset=Atelier.objects.none(),
        required=False,
    )
    equipe = forms.ModelChoiceField(
        label="Équipe",
        queryset=Equipe.objects.none(),
        required=False,
        help_text="Obligatoire pour un opérateur. Facultative à la création d’un collaborateur responsable.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.all().order_by("name")
        self.fields["atelier"].queryset = Atelier.objects.filter(actif=True)
        self.fields["equipe"].queryset = Equipe.objects.select_related("atelier").order_by("numero")

    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data.get("groups")
        group_names = {group.name for group in groups} if groups else set()
        is_admin = "Administrateurs" in group_names
        needs_team = "Opérateurs" in group_names

        if not is_admin and cleaned_data.get("atelier") is None:
            self.add_error("atelier", "L’atelier d’appartenance est obligatoire.")
        if needs_team and cleaned_data.get("equipe") is None:
            self.add_error("equipe", "Sélectionnez l’équipe de cet utilisateur.")
        if cleaned_data.get("equipe") and cleaned_data["equipe"].atelier_id != getattr(
            cleaned_data.get("atelier"), "pk", None
        ):
            self.add_error("equipe", "L’équipe doit appartenir à l’atelier sélectionné.")
        if "Administrateurs" in group_names and len(group_names) > 1:
            self.add_error("groups", "Un administrateur ne peut pas avoir un rôle métier.")
        return cleaned_data


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class EquipeAdminForm(forms.ModelForm):
    class Meta:
        model = Equipe
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = User.objects.filter(
            groups__name="Collaborateurs responsables"
        ).distinct().order_by("username")

    def clean(self):
        cleaned_data = super().clean()
        responsable = cleaned_data.get("responsable")
        atelier = cleaned_data.get("atelier")
        if responsable and not responsable.groups.filter(
            name="Collaborateurs responsables"
        ).exists():
            self.add_error(
                "responsable",
                "Le chef d’équipe doit avoir le rôle Collaborateur responsable.",
            )
        if responsable and atelier and getattr(responsable.profile, "atelier_id", None) != atelier.pk:
            self.add_error("responsable", "Le chef d’équipe doit appartenir à cet atelier.")
        return cleaned_data


@admin.register(User)
class UsineUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name",
                "last_name",
                "email",
                "password1",
                "password2",
                "groups",
                "atelier",
                "equipe",
            ),
        }),
    )
    list_display = ("username", "matricule", "get_full_name", "role", "atelier", "is_active", "is_staff")
    list_filter = ("groups", "is_active", "is_staff")
    search_fields = ("username", "matricule", "first_name", "last_name", "email")
    filter_horizontal = ("groups", "user_permissions")
    inlines = (UserProfileInline,)

    @admin.display(description="Atelier", ordering="profile__atelier")
    def atelier(self, user):
        return getattr(user.profile, "atelier", None) or ("—" if user.is_staff else "À définir")

    @admin.display(description="Matricule", ordering="profile__matricule")
    def matricule(self, user):
        return getattr(user.profile, "matricule", None) or "—"

    @admin.display(description="Rôle", ordering="groups__name")
    def role(self, user):
        roles = list(user.groups.values_list("name", flat=True))
        return ", ".join(roles) if roles else "Aucun rôle"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "groups" in form.base_fields:
            form.base_fields["groups"].label = "Rôle(s)"
            form.base_fields["groups"].help_text = (
                "Sélectionnez le rôle métier. Les permissions sont héritées du groupe."
            )
        return form

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        profile, _ = UserProfile.objects.get_or_create(user=obj)
        if not profile.matricule:
            profile.matricule = self._next_matricule()
            profile.save(update_fields=("matricule",))
        if "atelier" in form.cleaned_data:
            profile.atelier = form.cleaned_data["atelier"]
            profile.save(update_fields=("atelier",))

    @staticmethod
    def _next_matricule():
        from django.db.models import Max
        from django.db.models.functions import Cast, Substr, Length

        last = (
            UserProfile.objects.filter(matricule__startswith="UsineHA-")
            .aggregate(max_num=Max(Cast(Substr("matricule", 9), output_field=models.IntegerField())))
            .get("max_num")
        )
        next_num = (last or 0) + 1
        return f"UsineHA-{next_num:04d}"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        groups = set(form.instance.groups.values_list("name", flat=True))
        if "Collaborateurs responsables" in groups:
            groups.discard("Opérateurs")
            form.instance.groups.set(
                Group.objects.filter(name__in=groups)
            )
        elif "Opérateurs" in groups:
            groups.discard("Collaborateurs responsables")
            form.instance.groups.set(
                Group.objects.filter(name__in=groups)
            )
        equipe = form.cleaned_data.get("equipe")
        operator = Operateur.objects.filter(user=form.instance).first()
        if equipe is None and operator is not None:
            equipe = operator.equipe
        if "Collaborateurs responsables" in groups and equipe is not None:
            conflict = Equipe.objects.filter(
                pk=equipe.pk,
                responsable__isnull=False,
            ).exclude(responsable=form.instance).first()
            if conflict:
                messages.error(
                    request,
                    "Cette équipe possède déjà un autre collaborateur responsable.",
                )
            else:
                equipe.responsable = form.instance
                equipe.save(update_fields=("responsable",))
        if "Opérateurs" in groups and equipe is not None:
            Operateur.objects.update_or_create(
                user=form.instance,
                defaults={
                    "matricule": operator.matricule if operator else f"OP-{form.instance.pk:04d}",
                    "equipe": equipe,
                    "date_embauche": operator.date_embauche if operator else timezone.now().date(),
                },
            )


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    form = EquipeAdminForm
    list_display = ("numero", "designation", "atelier", "responsable")
    list_filter = ("atelier",)
    search_fields = ("numero", "designation", "responsable__username")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["responsable"].help_text = mark_safe(
            "Chef d’équipe obligatoire. "
            f'<a href="{reverse("admin:auth_user_add")}">Créer un collaborateur responsable</a>.'
        )
        return form


admin.site.register(Operateur)
