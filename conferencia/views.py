from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Min, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BuscaForm, NovaOSForm
from .models import ConclusaoBloqueada, FichaEntrada, ItemChecklist, OrdemServico
from .perfis import ATENDENTE, TECNICO, perfil_requerido, tem_perfil
from .services import criar_os_com_ficha

User = get_user_model()
ABERTOS = [OrdemServico.RECEBIDO, OrdemServico.EM_REPARO]


def _ctx(request, **extra):
    extra["eh_atendente"] = tem_perfil(request.user, ATENDENTE)
    extra["eh_tecnico"] = tem_perfil(request.user, TECNICO)
    return extra


@login_required
def inicio(request):
    form = BuscaForm(request.GET) if "numero_os" in request.GET else BuscaForm()
    nao_encontrada = False
    if form.is_bound and form.is_valid():
        numero = form.cleaned_data["numero_os"]
        if OrdemServico.objects.filter(numero_os=numero).exists():
            return redirect("detalhe", numero_os=numero)
        nao_encontrada = True
    carga = (
        User.objects.filter(groups__name=TECNICO, is_active=True)
        .annotate(
            em_aberto=Count("ordens", filter=Q(ordens__status__in=ABERTOS)),
            proxima=Min("ordens__data_prevista", filter=Q(ordens__status__in=ABERTOS)),
        )
        .order_by("first_name", "username")
    )
    return render(
        request,
        "conferencia/inicio.html",
        _ctx(request, form=form, nao_encontrada=nao_encontrada, carga=carga),
    )


@perfil_requerido(ATENDENTE)
def nova_os(request):
    if request.method == "POST":
        form = NovaOSForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                ordem = criar_os_com_ficha(usuario=request.user, **dados)
            except ValidationError as erro:
                form.add_error(None, " ".join(erro.messages))
            else:
                messages.success(request, f"OS {ordem.numero_os} registrada.")
                return redirect("detalhe", numero_os=ordem.numero_os)
    else:
        form = NovaOSForm()
    return render(request, "conferencia/nova_os.html", _ctx(request, form=form))


@login_required
def detalhe(request, numero_os):
    ordem = get_object_or_404(OrdemServico.objects.select_related("tecnico"), numero_os=numero_os)
    ficha = FichaEntrada.objects.filter(ordem_servico=ordem).first()
    itens = list(ordem.itens.select_related("teste"))
    resolvidos = sum(1 for i in itens if i.resultado != ItemChecklist.PENDENTE)
    return render(
        request,
        "conferencia/detalhe.html",
        _ctx(request, ordem=ordem, ficha=ficha, itens=itens, resolvidos=resolvidos, total=len(itens)),
    )


@require_POST
@perfil_requerido(TECNICO)
def iniciar_reparo(request, numero_os):
    ordem = get_object_or_404(OrdemServico, numero_os=numero_os)
    if ordem.status == OrdemServico.RECEBIDO:
        ordem.status = OrdemServico.EM_REPARO
        if ordem.tecnico_id is None:
            ordem.tecnico = request.user
        ordem.save(update_fields=["status", "tecnico"])
    else:
        messages.error(request, "Só uma OS recebida pode iniciar o reparo.")
    return redirect("detalhe", numero_os=ordem.numero_os)


@require_POST
@perfil_requerido(TECNICO)
def marcar_item(request, pk, resultado):
    if resultado not in (ItemChecklist.APROVADO, ItemChecklist.NAO_SE_APLICA):
        raise Http404
    item = get_object_or_404(ItemChecklist.objects.select_related("ordem_servico"), pk=pk)
    ordem = item.ordem_servico
    if ordem.status != OrdemServico.EM_REPARO:
        messages.error(request, "Inicie o reparo antes de marcar os testes.")
        return redirect("detalhe", numero_os=ordem.numero_os)
    item.resultado = resultado
    item.marcado_por = request.user
    item.marcado_em = timezone.now()
    item.save(update_fields=["resultado", "marcado_por", "marcado_em"])
    return redirect("detalhe", numero_os=ordem.numero_os)


@require_POST
@perfil_requerido(TECNICO)
def concluir(request, numero_os):
    ordem = get_object_or_404(OrdemServico, numero_os=numero_os)
    try:
        ordem.concluir()
    except ConclusaoBloqueada as erro:
        resolvidos = ordem.itens.exclude(resultado=ItemChecklist.PENDENTE).select_related("teste")
        return render(
            request,
            "conferencia/bloqueio.html",
            _ctx(request, ordem=ordem, pendentes=erro.pendentes, resolvidos=resolvidos),
        )
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
        return redirect("detalhe", numero_os=ordem.numero_os)
    itens = ordem.itens.select_related("teste")
    return render(
        request,
        "conferencia/pronta.html",
        _ctx(
            request,
            ordem=ordem,
            itens=itens,
            aprovados=itens.filter(resultado=ItemChecklist.APROVADO).count(),
            nao_se_aplica=itens.filter(resultado=ItemChecklist.NAO_SE_APLICA).count(),
        ),
    )


@require_POST
@perfil_requerido(ATENDENTE)
def avisar_cliente(request, numero_os):
    ordem = get_object_or_404(OrdemServico, numero_os=numero_os)
    if ordem.status == OrdemServico.PRONTO:
        ordem.status = OrdemServico.CLIENTE_AVISADO
        ordem.save(update_fields=["status"])
        messages.success(request, "Aviso ao cliente registrado.")
    else:
        messages.error(request, "Só uma OS pronta pode ter o aviso registrado.")
    return redirect("detalhe", numero_os=ordem.numero_os)
