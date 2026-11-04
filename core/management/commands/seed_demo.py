from datetime import date

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from maintenance.models import Incident, Machine, Maintenance
from production.models import Atelier, LigneProduction, LotProduction, Produit
from stock.models import Piece
from users.models import Equipe, Operateur, UserProfile


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration Usine HA."

    def handle(self, *args, **options):
        users = self.create_users()

        ateliers = [
            ("AT-01", "Assemblage final", "awa.kone"),
            ("AT-02", "Usinage de précision", "amadou.dosso"),
            ("AT-03", "Contrôle qualité", "mariama.coulibaly"),
        ]
        for numero, libelle, responsable in ateliers:
            Atelier.objects.update_or_create(
                numero=numero,
                defaults={"libelle": libelle, "responsable": users[responsable]},
            )
        profile_ateliers = {
            "awa.kone": "AT-01",
            "yannick.kouadio": "AT-02",
            "mariama.coulibaly": "AT-03",
        }
        for username, atelier_id in profile_ateliers.items():
            UserProfile.objects.update_or_create(
                user=users[username],
                defaults={"atelier_id": atelier_id},
            )

        lignes = [
            ("L-101", "AT-01", 4),
            ("L-102", "AT-01", 3),
            ("L-201", "AT-02", 5),
            ("L-301", "AT-03", 2),
        ]
        for numero, atelier_id, required in lignes:
            LigneProduction.objects.update_or_create(numero=numero, defaults={"atelier_id": atelier_id, "operateurs_requis": required})

        produits = [
            ("PRD-AX14", "Module de commande AX14", "1240"),
            ("PRD-BX08", "Boîtier de protection BX08", "860"),
        ]
        for reference, designation, quantity in produits:
            Produit.objects.update_or_create(reference=reference, defaults={"designation": designation, "prix_unitaire": "148.50", "quantite_stock": quantity})

        lots = [
            ("LOT-261101-A", "PRD-AX14", "L-101", 420, "en_cours"),
            ("LOT-261101-B", "PRD-BX08", "L-201", 280, "en_cours"),
            ("LOT-261031-C", "PRD-AX14", "L-102", 160, "termine"),
        ]
        for numero, product_id, line_id, quantity, status in lots:
            LotProduction.objects.update_or_create(numero_lot=numero, defaults={"produit_id": product_id, "ligne_id": line_id, "quantite": quantity, "statut": status})

        machines = [
            ("M-101", "Presse hydraulique", "L-101", "operationnelle"),
            ("M-102", "Visseuse automatique", "L-101", "maintenance"),
            ("M-201", "Centre d’usinage CNC", "L-201", "operationnelle"),
            ("M-301", "Banc de contrôle vision", "L-301", "operationnelle"),
        ]
        for identifiant, name, line_id, state in machines:
            Machine.objects.update_or_create(identifiant=identifiant, defaults={"nom": name, "ligne_id": line_id, "etat": state})

        Maintenance.objects.get_or_create(
            machine_id="M-102",
            description="Remplacement du module de vissage",
            defaults={
                "debut": timezone.now(),
                "duree_minutes": 90,
                "preventive": False,
            },
        )
        Maintenance.objects.get_or_create(
            machine_id="M-201",
            description="Graissage et contrôle préventif",
            defaults={
                "debut": timezone.now(),
                "duree_minutes": 45,
                "preventive": True,
            },
        )

        incident_data = [
            ("LOT-261101-A", "Défaut capteur", "Le capteur de pression remonte une valeur instable.", 24, "ouvert"),
            ("LOT-261101-B", "Arrêt matière", "Réapprovisionnement de matière première en attente.", 42, "en_cours"),
            ("LOT-261031-C", "Contrôle qualité", "Échantillon repassé en vérification dimensionnelle.", 15, "resolu"),
        ]
        for lot_id, kind, description, downtime, status in incident_data:
            Incident.objects.get_or_create(lot_id=lot_id, typologie=kind, defaults={"description": description, "arret_minutes": downtime, "statut": status})

        pieces = [
            ("PCE-CAP-04", "Capteur de pression 4–20 mA", "8"),
            ("PCE-VIS-M8", "Vis inox M8 × 30", "240"),
            ("PCE-FIL-02", "Filtre hydraulique", "4"),
            ("PCE-JNT-11", "Joint torique NBR", "67"),
        ]
        for reference, label, quantity in pieces:
            atelier_id = "AT-01" if reference in {"PCE-CAP-04", "PCE-VIS-M8"} else "AT-02"
            Piece.objects.update_or_create(
                reference=reference,
                defaults={
                    "libelle": label,
                    "prix_unitaire": "18.90",
                    "quantite_stock": quantity,
                    "atelier_id": atelier_id,
                },
            )

        teams = [
            ("EQ-A", "Équipe assemblage", "AT-01", users["awa.kone"]),
            ("EQ-B", "Équipe usinage", "AT-02", users["yannick.kouadio"]),
            ("EQ-C", "Équipe qualité", "AT-03", users["mariama.coulibaly"]),
        ]
        for numero, designation, atelier_id, responsable in teams:
            equipe, _ = Equipe.objects.update_or_create(
                numero=numero,
                defaults={
                    "designation": designation,
                    "atelier_id": atelier_id,
                    "responsable": responsable,
                },
            )
            operator_data = {
                "EQ-A": ("OP-001", users["awa.kone"], date(2022, 4, 11)),
                "EQ-B": ("OP-002", users["yannick.kouadio"], date(2023, 1, 16)),
                "EQ-C": ("OP-003", users["mariama.coulibaly"], date(2021, 9, 6)),
            }[numero]
            Operateur.objects.update_or_create(
                matricule=operator_data[0],
                defaults={"user": operator_data[1], "equipe": equipe, "date_embauche": operator_data[2]},
            )

        self.stdout.write(self.style.SUCCESS("Jeu de données Usine HA installé avec les utilisateurs ivoiriens."))

    def create_users(self):
        password = "UsineHA2026!"
        definitions = [
            ("amadou.dosso", "Amadou", "Dosso", "Administrateur", "Administrateurs"),
            ("awa.kone", "Awa", "Koné", "Responsable d’atelier", "Responsables d’ateliers"),
            ("yannick.kouadio", "Yannick", "Kouadio", "Responsable d’équipe", "Collaborateurs responsables"),
            ("mariama.coulibaly", "Mariama", "Coulibaly", "Opératrice terrain", "Opérateurs"),
        ]
        users = {}
        for username, first_name, last_name, role, group_name in definitions:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first_name, "last_name": last_name},
            )
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = True
            user.set_password(password)
            user.save()
            group = Group.objects.get_or_create(name=group_name)[0]
            group.permissions.set(self.permissions_for_group(group_name))
            user.groups.set([group])
            if group_name == "Administrateurs":
                user.is_staff = True
                user.save(update_fields=["is_staff"])
            users[username] = user
        return users

    @staticmethod
    def permissions_for_group(group_name):
        if group_name == "Administrateurs":
            return Permission.objects.all()
        permission_map = {
            "Responsables d’ateliers": {
                Atelier: ("view", "add", "change"),
                LigneProduction: ("view", "add", "change"),
                Produit: ("view", "add", "change"),
                LotProduction: ("view", "add", "change"),
                Machine: ("view",),
                Incident: ("view", "add", "change"),
                Piece: ("view", "add", "change"),
                Maintenance: ("view", "add", "change"),
            },
            "Collaborateurs responsables": {
                Equipe: ("view", "add", "change"),
                Operateur: ("view", "add", "change"),
                Machine: ("view",),
                Incident: ("view", "add", "change"),
                LotProduction: ("view",),
                Piece: ("view", "change"),
                Maintenance: ("view", "add", "change", "delete"),
            },
            "Opérateurs": {
                Machine: ("view",),
                Incident: ("view", "add"),
                Piece: ("view", "change"),
                Maintenance: ("view", "add", "change", "delete"),
            },
        }
        permissions = []
        for model, actions in permission_map[group_name].items():
            content_type = ContentType.objects.get_for_model(model)
            permissions.extend(
                Permission.objects.filter(
                    content_type=content_type,
                    codename__in=[f"{action}_{model._meta.model_name}" for action in actions],
                )
            )
        return permissions

