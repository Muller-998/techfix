from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("entrar/", auth_views.LoginView.as_view(template_name="conferencia/login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("os/nova/", views.nova_os, name="nova_os"),
    re_path(r"^os/(?P<numero_os>[0-9]{4,8})/$", views.detalhe, name="detalhe"),
    re_path(r"^os/(?P<numero_os>[0-9]{4,8})/iniciar/$", views.iniciar_reparo, name="iniciar_reparo"),
    re_path(r"^os/(?P<numero_os>[0-9]{4,8})/concluir/$", views.concluir, name="concluir"),
    re_path(r"^os/(?P<numero_os>[0-9]{4,8})/avisar/$", views.avisar_cliente, name="avisar_cliente"),
    path("item/<int:pk>/<str:resultado>/", views.marcar_item, name="marcar_item"),
]
