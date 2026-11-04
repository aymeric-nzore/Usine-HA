from django.db.models import Count, Sum
from functools import wraps

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode

from maintenance.models import Incident, Machine, Maintenance
from production.models import Atelier, LigneProduction, LotProduction, Produit
from stock.models import Piece
from .forms import (
    AtelierSelectionForm,
    IncidentForm,
    MaintenanceForm,
    PieceForm,
    ProductForm,
    TeamLoginForm,
    available_ateliers,
)


def operational_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if request.user.is_staff:
            return redirect("/admin/")
        if "atelier_id" not in request.session:
            return redirect(f"{reverse('atelier_selection')}?{urlencode({'next': request.get_full_path()})}")
        if not available_ateliers(request.user).filter(
            pk=request.session["atelier_id"]
        ).exists():
            request.session.pop("atelier_id", None)
            return redirect("atelier_selection")
        return view_func(request, *args, **kwargs)

    return wrapped


class TeamLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = TeamLoginForm

    def form_valid(self, form):
        self.request.session["atelier_id"] = form.cleaned_data["atelier"].pk
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, {self.request.get_host()}
        ):
            return next_url
        return reverse("dashboard")


def logout_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("La déconnexion doit utiliser POST.")
    logout(request)
    return redirect("login")


def atelier_selection(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    if request.user.is_staff:
        return redirect("/admin/")
    form = AtelierSelectionForm(request.user, request.POST or None)
    if form.is_valid():
        request.session["atelier_id"] = form.cleaned_data["atelier"].pk
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, {request.get_host()}
        ):
            return redirect(next_url)
        return redirect("dashboard")
    return render(request, "registration/atelier_selection.html", {
        "form": form,
        "next": request.GET.get("next", ""),
    })


def selected_atelier(request):
    return get_object_or_404(
        Atelier,
        pk=request.session["atelier_id"],
        responsable__isnull=False,
    )


@operational_required
def dashboard(request):
    atelier = selected_atelier(request)
    context = {
        "atelier": atelier,
        "ateliers": Atelier.objects.filter(pk=atelier.pk).annotate(line_count=Count("lignes")),
        "machines": Machine.objects.filter(ligne__atelier=atelier).select_related("ligne")[:6],
        "recent_incidents": Incident.objects.filter(lot__ligne__atelier=atelier).select_related("lot").order_by("-created_at")[:5],
        "stats": {
            "ateliers": 1,
            "production": LotProduction.objects.filter(ligne__atelier=atelier, statut="en_cours").count(),
            "machines": Machine.objects.filter(ligne__atelier=atelier).count(),
            "stock_alerts": Piece.objects.filter(atelier=atelier, quantite_stock__lte=10).count(),
        },
        "production_total": LotProduction.objects.filter(ligne__atelier=atelier, statut="en_cours").aggregate(total=Sum("quantite")).get("total") or 0,
    }
    return render(request, "core/dashboard.html", context)


@operational_required
@permission_required("production.view_atelier", raise_exception=True)
def atelier_list(request):
    atelier = selected_atelier(request)
    lines = LigneProduction.objects.filter(atelier=atelier).prefetch_related("machines")
    return render(request, "core/ateliers.html", {
        "atelier": atelier,
        "lines": lines,
    })


@operational_required
@permission_required("production.view_lotproduction", raise_exception=True)
def production_list(request):
    atelier = selected_atelier(request)
    lots = LotProduction.objects.filter(ligne__atelier=atelier).select_related(
        "produit", "ligne"
    )
    return render(request, "core/production.html", {
        "atelier": atelier,
        "lots": lots,
        "products": Produit.objects.filter(lotproduction__ligne__atelier=atelier).distinct(),
    })


@operational_required
@permission_required("production.view_lotproduction", raise_exception=True)
def stats_production(request):
    """Statistiques de production pour le responsable d'atelier."""
    atelier = selected_atelier(request)
    lots = LotProduction.objects.filter(ligne__atelier=atelier).select_related("produit", "ligne")

    total_lots = lots.count()
    lots_en_cours = lots.filter(statut="en_cours").count()
    lots_termines = lots.filter(statut="termine").count()
    lots_bloques = lots.filter(statut="bloque").count()
    quantite_totale = lots.aggregate(total=Sum("quantite")).get("total") or 0

    # Production par ligne
    production_par_ligne = (
        lots.values("ligne__numero")
        .annotate(nb_lots=Count("numero_lot"), qte=Sum("quantite"))
        .order_by("ligne__numero")
    )

    # Production par produit
    production_par_produit = (
        lots.values("produit__reference", "produit__designation")
        .annotate(nb_lots=Count("numero_lot"), qte=Sum("quantite"))
        .order_by("-qte")
    )

    # Incidents et temps d'arrêt
    incidents = Incident.objects.filter(lot__ligne__atelier=atelier).select_related("lot")
    total_incidents = incidents.count()
    arret_total_minutes = incidents.aggregate(total=Sum("arret_minutes")).get("total") or 0

    # Machines en maintenance ou arrêt
    machines = Machine.objects.filter(ligne__atelier=atelier)
    machines_maintenance = machines.filter(etat="maintenance").count()
    machines_arret = machines.filter(etat="arret").count()

    context = {
        "atelier": atelier,
        "total_lots": total_lots,
        "lots_en_cours": lots_en_cours,
        "lots_termines": lots_termines,
        "lots_bloques": lots_bloques,
        "quantite_totale": quantite_totale,
        "production_par_ligne": production_par_ligne,
        "production_par_produit": production_par_produit,
        "total_incidents": total_incidents,
        "arret_total_minutes": arret_total_minutes,
        "machines_maintenance": machines_maintenance,
        "machines_arret": machines_arret,
        "machines_total": machines.count(),
    }
    return render(request, "core/stats_production.html", context)


@operational_required
@permission_required("maintenance.view_incident", raise_exception=True)
def incident_feed(request):
    atelier = selected_atelier(request)
    status = request.GET.get("status", "all")
    incidents = Incident.objects.filter(lot__ligne__atelier=atelier).select_related("lot").order_by("-created_at")
    if status in {"ouvert", "en_cours", "resolu"}:
        incidents = incidents.filter(statut=status)
    return render(request, "core/partials/incident_feed.html", {"incidents": incidents[:8], "active_status": status})


@operational_required
@permission_required("maintenance.view_incident", raise_exception=True)
def incident_list(request):
    atelier = selected_atelier(request)
    return render(request, "core/incidents.html", {
        "atelier": atelier,
        "incidents": Incident.objects.filter(lot__ligne__atelier=atelier).select_related("lot").order_by("-created_at"),
    })


@operational_required
@permission_required("maintenance.add_incident", raise_exception=True)
def incident_create(request):
    form = IncidentForm(selected_atelier(request), request.POST or None)
    if form.is_valid():
        incident = form.save()
        messages.success(request, f"{incident} a été créé.")
        return redirect("incident_list")
    return render(request, "core/incident_form.html", {"form": form, "title": "Déclarer un incident"})


@operational_required
@permission_required("maintenance.change_incident", raise_exception=True)
def incident_update(request, incident_id):
    atelier = selected_atelier(request)
    incident = get_object_or_404(Incident, pk=incident_id, lot__ligne__atelier=atelier)
    form = IncidentForm(atelier, request.POST or None, instance=incident)
    if form.is_valid():
        form.save()
        messages.success(request, f"{incident} a été mis à jour.")
        return redirect("incident_list")
    return render(request, "core/incident_form.html", {"form": form, "title": f"Modifier {incident}"})


@operational_required
@permission_required("maintenance.delete_incident", raise_exception=True)
def incident_delete(request, incident_id):
    incident = get_object_or_404(Incident, pk=incident_id, lot__ligne__atelier=selected_atelier(request))
    if request.method == "POST":
        incident.delete()
        messages.success(request, "L’incident a été supprimé.")
        return redirect("incident_list")
    return render(request, "core/confirm_delete.html", {"object": incident, "cancel_url": "incident_list"})


@operational_required
@permission_required("stock.view_piece", raise_exception=True)
def piece_list(request):
    return render(request, "core/pieces.html", {"pieces": Piece.objects.filter(atelier=selected_atelier(request)).order_by("reference")})


@operational_required
@permission_required("stock.add_piece", raise_exception=True)
def piece_create(request):
    form = PieceForm(selected_atelier(request), request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "La pièce a été ajoutée.")
        return redirect("piece_list")
    return render(request, "core/piece_form.html", {"form": form, "title": "Ajouter une pièce"})


@operational_required
@permission_required("stock.change_piece", raise_exception=True)
def piece_update(request, reference):
    atelier = selected_atelier(request)
    piece = get_object_or_404(Piece, pk=reference, atelier=atelier)
    form = PieceForm(atelier, request.POST or None, instance=piece)
    if form.is_valid():
        form.save()
        messages.success(request, "La pièce a été mise à jour.")
        return redirect("piece_list")
    return render(request, "core/piece_form.html", {"form": form, "title": f"Modifier {piece.reference}"})


@operational_required
@permission_required("stock.delete_piece", raise_exception=True)
def piece_delete(request, reference):
    piece = get_object_or_404(Piece, pk=reference, atelier=selected_atelier(request))
    if request.method == "POST":
        piece.delete()
        messages.success(request, "La pièce a été supprimée.")
        return redirect("piece_list")
    return render(request, "core/confirm_delete.html", {"object": piece, "cancel_url": "piece_list"})


@operational_required
@permission_required("maintenance.view_maintenance", raise_exception=True)
def maintenance_list(request):
    maintenances = Maintenance.objects.filter(machine__ligne__atelier=selected_atelier(request)).select_related("machine").order_by("-debut")
    return render(request, "core/maintenance.html", {"maintenances": maintenances})


@operational_required
@permission_required("maintenance.add_maintenance", raise_exception=True)
def maintenance_create(request):
    form = MaintenanceForm(selected_atelier(request), request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "L’intervention de maintenance a été planifiée.")
        return redirect("maintenance_list")
    return render(request, "core/maintenance_form.html", {"form": form, "title": "Planifier une maintenance"})


@operational_required
@permission_required("maintenance.change_maintenance", raise_exception=True)
def maintenance_update(request, maintenance_id):
    atelier = selected_atelier(request)
    maintenance = get_object_or_404(Maintenance, pk=maintenance_id, machine__ligne__atelier=atelier)
    form = MaintenanceForm(atelier, request.POST or None, instance=maintenance)
    if form.is_valid():
        form.save()
        messages.success(request, "L’intervention de maintenance a été mise à jour.")
        return redirect("maintenance_list")
    return render(request, "core/maintenance_form.html", {"form": form, "title": "Modifier la maintenance"})


@operational_required
@permission_required("maintenance.delete_maintenance", raise_exception=True)
def maintenance_delete(request, maintenance_id):
    maintenance = get_object_or_404(Maintenance, pk=maintenance_id, machine__ligne__atelier=selected_atelier(request))
    if request.method == "POST":
        maintenance.delete()
        messages.success(request, "L’intervention de maintenance a été supprimée.")
        return redirect("maintenance_list")
    return render(request, "core/confirm_delete.html", {"object": maintenance, "cancel_url": "maintenance_list"})


@operational_required
@permission_required("production.view_produit", raise_exception=True)
def product_list(request):
    atelier = selected_atelier(request)
    produits = Produit.objects.all().order_by("reference")
    return render(request, "core/product_list.html", {
        "atelier": atelier,
        "produits": produits,
    })


@operational_required
@permission_required("production.add_produit", raise_exception=True)
def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Le produit a été créé.")
        return redirect("product_list")
    return render(request, "core/product_form.html", {
        "form": form,
        "title": "Ajouter un produit",
    })


@operational_required
@permission_required("production.change_produit", raise_exception=True)
def product_update(request, reference):
    produit = get_object_or_404(Produit, reference=reference)
    form = ProductForm(request.POST or None, instance=produit)
    if form.is_valid():
        form.save()
        messages.success(request, "Le produit a été mis à jour.")
        return redirect("product_list")
    return render(request, "core/product_form.html", {
        "form": form,
        "title": f"Modifier {produit.reference}",
    })


@operational_required
@permission_required("production.delete_produit", raise_exception=True)
def product_delete(request, reference):
    produit = get_object_or_404(Produit, reference=reference)
    if request.method == "POST":
        produit.delete()
        messages.success(request, "Le produit a été supprimé.")
        return redirect("product_list")
    return render(request, "core/confirm_delete.html", {"object": produit, "cancel_url": "product_list"})
