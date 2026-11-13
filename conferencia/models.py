from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

# \A e \Z evitam aceitar quebra de linha no fim; [0-9] evita dígitos de outros alfabetos.
validar_numero_os = RegexValidator(
    regex=r"\A[0-9]{4,8}\Z",
    message="O número da OS deve ter de 4 a 8 dígitos. Digite só números.",
)

TIPOS_APARELHO = [
    ("celular", "Celular"),
    ("notebook", "Notebook"),
    ("videogame", "Videogame"),
    ("outro", "Outro"),
]


class ConclusaoBloqueada(Exception):
    """A OS não pode ir para 'pronto' enquanto houver teste pendente."""

    def __init__(self, pendentes):
        super().__init__("Há testes pendentes.")
        self.pendentes = list(pendentes)


class TesteModelo(models.Model):
    tipo_aparelho = models.CharField(max_length=20, choices=TIPOS_APARELHO)
    nome_teste = models.CharField(max_length=60)
    ordem = models.PositiveSmallIntegerField(default=1)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo_aparelho", "ordem", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_aparelho", "nome_teste"], name="teste_unico_por_tipo"
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_aparelho_display()}: {self.nome_teste}"


class OrdemServico(models.Model):
    RECEBIDO = "recebido"
    EM_REPARO = "em_reparo"
    PRONTO = "pronto"
    CLIENTE_AVISADO = "cliente_avisado"
    STATUS = [
        (RECEBIDO, "Recebido"),
        (EM_REPARO, "Em reparo"),
        (PRONTO, "Pronto"),
        (CLIENTE_AVISADO, "Cliente avisado"),
    ]

    numero_os = models.CharField(
        "Número da OS", max_length=8, unique=True, validators=[validar_numero_os]
    )
    tipo_aparelho = models.CharField(max_length=20, choices=TIPOS_APARELHO)
    descricao_curta = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS, default=RECEBIDO)
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ordens",
    )
    data_prevista = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return f"OS {self.numero_os}"

    def clean(self):
        if self.tecnico_id and not self.tecnico.groups.filter(name="Tecnico").exists():
            raise ValidationError(
                {"tecnico": "Só usuário do grupo Tecnico pode ser responsável."}
            )

    def itens_pendentes(self):
        return self.itens.filter(resultado=ItemChecklist.PENDENTE).select_related("teste")

    def concluir(self):
        """Muda para 'pronto' só se estiver em reparo e sem item pendente."""
        if self.status != self.EM_REPARO:
            raise ValidationError("A OS precisa estar em reparo para ser concluída.")
        pendentes = self.itens_pendentes()
        if pendentes.exists():
            raise ConclusaoBloqueada(pendentes)
        self.status = self.PRONTO
        self.concluida_em = timezone.now()
        self.save(update_fields=["status", "concluida_em"])


class FichaEntrada(models.Model):
    ordem_servico = models.OneToOneField(
        OrdemServico, on_delete=models.CASCADE, related_name="ficha"
    )
    acessorios_recebidos = models.CharField(max_length=200)
    estado_visivel = models.CharField(max_length=200)
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fichas_registradas",
    )
    registrada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ficha da {self.ordem_servico}"


class ItemChecklist(models.Model):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    NAO_SE_APLICA = "nao_se_aplica"
    RESULTADOS = [
        (PENDENTE, "Pendente"),
        (APROVADO, "Aprovado"),
        (NAO_SE_APLICA, "Não se aplica"),
    ]

    ordem_servico = models.ForeignKey(
        OrdemServico, on_delete=models.CASCADE, related_name="itens"
    )
    teste = models.ForeignKey(TesteModelo, on_delete=models.PROTECT)
    resultado = models.CharField(max_length=20, choices=RESULTADOS, default=PENDENTE)
    marcado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="itens_marcados",
    )
    marcado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["teste__ordem", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["ordem_servico", "teste"], name="item_unico_por_os_e_teste"
            )
        ]

    def __str__(self):
        return f"{self.ordem_servico}: {self.teste.nome_teste} ({self.resultado})"
