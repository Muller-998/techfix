from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ATENDENTE = "Atendente"
TECNICO = "Tecnico"


def tem_perfil(user, perfil):
    return user.is_authenticated and user.groups.filter(name=perfil).exists()


def perfil_requerido(perfil):
    """Exige login e o perfil indicado. Sem o perfil, responde 403 (negar por padrão)."""

    def decorador(view):
        @wraps(view)
        def interna(request, *args, **kwargs):
            if not tem_perfil(request.user, perfil):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return login_required(interna)

    return decorador
