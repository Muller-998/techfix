from django.contrib import admin

from .models import FichaEntrada, ItemChecklist, OrdemServico, TesteModelo

admin.site.register(OrdemServico)
admin.site.register(FichaEntrada)
admin.site.register(TesteModelo)
admin.site.register(ItemChecklist)
