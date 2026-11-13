from django.db import transaction

from .models import FichaEntrada, ItemChecklist, OrdemServico, TesteModelo


@transaction.atomic
def criar_os_com_ficha(
    *,
    numero_os,
    tipo_aparelho,
    descricao_curta,
    acessorios_recebidos,
    estado_visivel,
    usuario,
    tecnico=None,
    data_prevista=None,
):
    """Cria a OS, a ficha de entrada e o checklist com os testes ativos do tipo."""
    ordem = OrdemServico(
        numero_os=numero_os,
        tipo_aparelho=tipo_aparelho,
        descricao_curta=descricao_curta,
        tecnico=tecnico,
        data_prevista=data_prevista,
    )
    ordem.full_clean()
    ordem.save()
    FichaEntrada.objects.create(
        ordem_servico=ordem,
        acessorios_recebidos=acessorios_recebidos,
        estado_visivel=estado_visivel,
        registrada_por=usuario,
    )
    testes = TesteModelo.objects.filter(tipo_aparelho=tipo_aparelho, ativo=True)
    ItemChecklist.objects.bulk_create(
        [ItemChecklist(ordem_servico=ordem, teste=t) for t in testes]
    )
    return ordem
