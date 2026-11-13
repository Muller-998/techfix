from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Inclui as rotas diretamente na raiz sem travar em namespaces parciais
    path('', include('conferencia.urls')),

]