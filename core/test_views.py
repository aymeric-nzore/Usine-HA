from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from maintenance.models import Incident, Machine, Maintenance
from production.models import Atelier, LigneProduction, LotProduction, Produit
from stock.models import Piece
from users.models import UserProfile


class OperationalCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="awa.kone",
            password="secure-test-password",
        )
        self.client.login(username="awa.kone", password="secure-test-password")
        incident_type = ContentType.objects.get_for_model(Incident)
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type=incident_type,
                codename="view_incident",
            )
        )
        self.product = Produit.objects.create(
            reference="PRD-TEST",
            designation="Produit de test",
            prix_unitaire="10.00",
        )
        atelier = Atelier.objects.create(
            numero="AT-TEST",
            libelle="Atelier test",
            responsable=self.user,
        )
        UserProfile.objects.filter(user=self.user).update(atelier=atelier)
        self.line = LigneProduction.objects.create(
            numero="L-TEST",
            atelier=atelier,
            operateurs_requis=2,
        )
        self.lot = LotProduction.objects.create(
            numero_lot="LOT-TEST",
            produit=self.product,
            ligne=self.line,
            quantite=10,
        )
        self.client.session["atelier_id"] = atelier.pk
        self.client.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.client.session.session_key
        self.client.force_login(self.user)
        self.client.session["atelier_id"] = atelier.pk
        self.client.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.client.session.session_key
        self.client.post(
            reverse("atelier_selection"),
            {"atelier": atelier.pk},
        )
        self.client.login(username="awa.kone", password="secure-test-password")
        self.client.session["atelier_id"] = atelier.pk
        self.client.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.client.session.session_key

    def test_incident_list_is_available_to_authenticated_users(self):
        response = self.client.get(reverse("incident_list"))
        self.assertEqual(response.status_code, 200)

    def test_atelier_and_production_pages_are_available_with_permissions(self):
        permissions = Permission.objects.filter(
            content_type__app_label="production",
            codename__in=("view_atelier", "view_lotproduction"),
        )
        self.user.user_permissions.add(*permissions)

        atelier_response = self.client.get(reverse("atelier_list"))
        self.assertEqual(atelier_response.status_code, 200)
        self.assertContains(atelier_response, "L-TEST")

        production_response = self.client.get(reverse("production_list"))
        self.assertEqual(production_response.status_code, 200)
        self.assertContains(production_response, "LOT-TEST")

    def test_incident_create_saves_submitted_form(self):
        incident_type = ContentType.objects.get_for_model(Incident)
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type=incident_type,
                codename__in=("add_incident",),
            )
        )
        response = self.client.post(
            reverse("incident_create"),
            {
                "lot": self.lot.pk,
                "typologie": "Arrêt de test",
                "description": "Description de l’incident de test.",
                "arret_minutes": 12,
                "statut": "ouvert",
            },
        )
        self.assertRedirects(response, reverse("incident_list"))
        self.assertTrue(Incident.objects.filter(typologie="Arrêt de test").exists())

    def test_piece_list_is_forbidden_without_piece_permission(self):
        response = self.client.get(reverse("piece_list"))
        self.assertEqual(response.status_code, 403)

    def test_piece_create_saves_submitted_form(self):
        piece_type = ContentType.objects.get_for_model(Piece)
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type=piece_type,
                codename__in=("add_piece", "view_piece"),
            )
        )
        response = self.client.post(
            reverse("piece_create"),
            {
                "reference": "PCE-TEST",
                "libelle": "Joint de test",
                "prix_unitaire": "4.50",
                "quantite_stock": 18,
                "seuil_alerte": 5,
            },
        )
        self.assertRedirects(response, reverse("piece_list"))
        self.assertTrue(Piece.objects.filter(reference="PCE-TEST").exists())

    def test_maintenance_create_requires_permission_and_saves(self):
        machine = Machine.objects.create(
            identifiant="M-TEST",
            nom="Machine test",
            ligne=self.line,
        )
        maintenance_type = ContentType.objects.get_for_model(Maintenance)
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type=maintenance_type,
                codename__in=("view_maintenance", "add_maintenance"),
            )
        )
        response = self.client.post(
            reverse("maintenance_create"),
            {
                "machine": machine.pk,
                "description": "Contrôle de sécurité",
                "debut": "2026-11-01T08:30",
                "duree_minutes": 30,
                "preventive": "on",
            },
        )
        self.assertRedirects(response, reverse("maintenance_list"))
        self.assertTrue(Maintenance.objects.filter(description="Contrôle de sécurité").exists())

    def test_maintenance_list_is_forbidden_without_maintenance_permission(self):
        response = self.client.get(reverse("maintenance_list"))
        self.assertEqual(response.status_code, 403)

    def test_incidents_from_another_atelier_are_not_visible(self):
        other_atelier = Atelier.objects.create(
            numero="AT-OTHER",
            libelle="Autre atelier",
            responsable=get_user_model().objects.create_user(
                username="other.manager",
                password="secure-other-password",
            ),
        )
        other_line = LigneProduction.objects.create(
            numero="L-OTHER",
            atelier=other_atelier,
            operateurs_requis=1,
        )
        LotProduction.objects.create(
            numero_lot="LOT-OTHER",
            produit=self.product,
            ligne=other_line,
            quantite=5,
        )
        Incident.objects.create(
            lot_id="LOT-OTHER",
            typologie="Incident isolé",
            description="Ne doit pas apparaître dans l’atelier courant.",
            arret_minutes=2,
        )
        response = self.client.get(reverse("incident_list"))
        self.assertNotContains(response, "Incident isolé")
