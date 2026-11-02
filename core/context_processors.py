from production.models import Atelier


def current_atelier(request):
    atelier = None
    atelier_id = request.session.get("atelier_id")
    if atelier_id and request.user.is_authenticated:
        atelier = Atelier.objects.filter(pk=atelier_id).first()
    return {"atelier": atelier}
