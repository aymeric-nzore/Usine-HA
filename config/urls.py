"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('ateliers/', views.atelier_list, name='atelier_list'),
    path('production/', views.production_list, name='production_list'),
    path('production/statistiques/', views.stats_production, name='stats_production'),
    path('incidents/', views.incident_list, name='incident_list'),
    path('incidents/nouveau/', views.incident_create, name='incident_create'),
    path('incidents/<int:incident_id>/modifier/', views.incident_update, name='incident_update'),
    path('incidents/<int:incident_id>/supprimer/', views.incident_delete, name='incident_delete'),
    path('incidents/flux/', views.incident_feed, name='incident_feed'),
    path('pieces/', views.piece_list, name='piece_list'),
    path('pieces/nouvelle/', views.piece_create, name='piece_create'),
    path('pieces/<str:reference>/modifier/', views.piece_update, name='piece_update'),
    path('pieces/<str:reference>/supprimer/', views.piece_delete, name='piece_delete'),
    path('produits/', views.product_list, name='product_list'),
    path('produits/nouveau/', views.product_create, name='product_create'),
    path('produits/<str:reference>/modifier/', views.product_update, name='product_update'),
    path('produits/<str:reference>/supprimer/', views.product_delete, name='product_delete'),
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/nouvelle/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/<int:maintenance_id>/modifier/', views.maintenance_update, name='maintenance_update'),
    path('maintenance/<int:maintenance_id>/supprimer/', views.maintenance_delete, name='maintenance_delete'),
    path('connexion/', views.TeamLoginView.as_view(), name='login'),
    path('ateliers/selection/', views.atelier_selection, name='atelier_selection'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('mot-de-passe/modifier/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
]
