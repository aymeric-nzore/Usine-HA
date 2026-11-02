from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from maintenance.models import Incident, Machine, Maintenance
from production.models import LotProduction
from stock.models import Piece
from production.models import Atelier
from users.models import Equipe, Operateur, UserProfile
from users.admin import AdminUserCreationForm


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="m.curie",
            password="secure-test-password",
            first_name="Marie",
            last_name="Curie",
        )
        self.atelier = Atelier.objects.create(
            numero="AT-AUTH",
            libelle="Atelier authentification",
            responsable=self.user,
        )
        self.user.profile.atelier = self.atelier
        self.user.profile.save(update_fields=("atelier",))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_login_form_lists_active_ateliers(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, 'id="id_atelier"')
        self.assertContains(response, "AT-AUTH")
        self.assertContains(response, "awa.kone")

    def test_user_can_login_and_logout(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "m.curie",
                "password": "secure-test-password",
                "atelier": self.atelier.pk,
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_staff_user_cannot_use_operational_login(self):
        admin = get_user_model().objects.create_user(
            username="amadou.dosso",
            password="secure-admin-password",
            is_staff=True,
        )
        response = self.client.post(
            reverse("login"),
            {"username": admin.username, "password": "secure-admin-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "administrateurs se connectent")

    def test_login_requires_an_atelier_belonging_to_user(self):
        response = self.client.post(
            reverse("login"),
            {"username": "m.curie", "password": "secure-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sélectionnez votre atelier")

        response = self.client.post(
            reverse("login"),
            {
                "username": "m.curie",
                "password": "secure-test-password",
                "atelier": self.atelier.pk,
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(response.wsgi_request.session["atelier_id"], self.atelier.pk)

    def test_staff_is_sent_to_admin_from_operational_dashboard(self):
        self.client.force_login(self.user)
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, "/admin/")

    def test_collaborator_role_includes_operator_permissions(self):
        group = Group.objects.create(name="Collaborateur de test")
        for model, actions in (
            (Machine, ("view",)),
            (Incident, ("view", "add", "change")),
            (Maintenance, ("view", "add", "change", "delete")),
            (Piece, ("view", "change")),
            (LotProduction, ("view",)),
        ):
            content_type = ContentType.objects.get_for_model(model)
            group.permissions.add(
                *Permission.objects.filter(
                    content_type=content_type,
                    codename__in=[
                        f"{action}_{model._meta.model_name}" for action in actions
                    ],
                )
            )
        self.user.groups.add(group)
        self.assertTrue(self.user.has_perm("maintenance.view_machine"))
        self.assertTrue(self.user.has_perm("maintenance.add_maintenance"))
        self.assertTrue(self.user.has_perm("stock.change_piece"))
        self.assertTrue(self.user.has_perm("production.view_lotproduction"))

    def test_admin_user_list_displays_role_column(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.test",
            password="secure-admin-password",
            email="admin@example.com",
        )
        role = Group.objects.create(name="Responsables de test")
        admin.groups.add(role)
        self.client.force_login(admin)
        response = self.client.get("/admin/auth/user/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rôle")
        self.assertContains(response, "Responsables de test")

    def test_user_has_editable_atelier_profile_in_admin(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.atelier",
            password="secure-admin-password",
            email="admin.atelier@example.com",
        )
        self.client.force_login(admin)
        response = self.client.get(f"/admin/auth/user/{self.user.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atelier")
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_admin_can_open_user_creation_page(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.creation",
            password="secure-admin-password",
            email="admin.creation@example.com",
        )
        self.client.force_login(admin)
        response = self.client.get("/admin/auth/user/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, "Atelier")

    def test_admin_can_create_operator_with_role_atelier_and_team(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.operator",
            password="secure-admin-password",
            email="admin.operator@example.com",
        )
        operator_group = Group.objects.create(name="Opérateurs")
        responsible_group = Group.objects.create(name="Collaborateurs responsables")
        responsible = get_user_model().objects.create_user(
            username="team.lead",
            password="secure-team-password",
        )
        responsible.groups.add(responsible_group)
        responsible.profile.atelier = self.atelier
        responsible.profile.save(update_fields=("atelier",))
        team = Equipe.objects.create(
            numero="EQ-AUTH",
            designation="Équipe test",
            atelier=self.atelier,
            responsable=responsible,
        )
        self.client.force_login(admin)
        response = self.client.post(
            "/admin/auth/user/add/",
            {
                "username": "operator.admin",
                "first_name": "Opérateur",
                "last_name": "Test",
                "email": "operator@example.com",
                "password1": "SecureOperator123!",
                "password2": "SecureOperator123!",
                "groups": [operator_group.pk],
                "atelier": self.atelier.pk,
                "equipe": team.pk,
                "_save": "Enregistrer",
            },
        )
        self.assertEqual(response.status_code, 302)
        operator_user = get_user_model().objects.get(username="operator.admin")
        self.assertEqual(operator_user.profile.atelier, self.atelier)
        self.assertEqual(
            Operateur.objects.get(user=operator_user).equipe,
            team,
        )

    def test_admin_can_create_collaborator_without_team(self):
        collaborator_group = Group.objects.create(name="Collaborateurs responsables")
        form = AdminUserCreationForm(
            data={
                "username": "collaborator.pending",
                "first_name": "Chef",
                "last_name": "Équipe",
                "email": "chef@example.com",
                "password1": "VioletRiver903!",
                "password2": "VioletRiver903!",
                "groups": [collaborator_group.pk],
                "atelier": self.atelier.pk,
                "equipe": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_team_admin_form_offers_collaborator_creation_link(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.team-link",
            password="secure-admin-password",
            email="admin.team-link@example.com",
        )
        self.client.force_login(admin)
        response = self.client.get("/admin/users/equipe/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Créer un collaborateur responsable")
