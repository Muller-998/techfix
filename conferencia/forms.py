from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import TIPOS_APARELHO, OrdemServico, validar_numero_os
from .perfis import TECNICO

User = get_user_model()


class BuscaForm(forms.Form):
    numero_os = forms.CharField(
        label="Número da OS",
        help_text="4 a 8 dígitos, só números",
        validators=[validar_numero_os],
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
        error_messages={"required": "Informe o número da OS."},
    )


class NovaOSForm(forms.Form):
    numero_os = forms.CharField(
        label="Número da OS",
        help_text="Número emitido no programa da loja (4 a 8 dígitos)",
        validators=[validar_numero_os],
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
        error_messages={"required": "Informe o número da OS."},
    )
    tipo_aparelho = forms.ChoiceField(label="Tipo do aparelho", choices=TIPOS_APARELHO)
    descricao_curta = forms.CharField(
        label="Descrição curta",
        max_length=80,
        error_messages={"required": "Informe uma descrição curta, por exemplo iPhone 13."},
    )
    acessorios_recebidos = forms.CharField(
        label="Acessórios recebidos",
        max_length=200,
        error_messages={"required": 'Informe os acessórios recebidos ou escreva "nenhum".'},
    )
    estado_visivel = forms.CharField(
        label="Estado visível",
        max_length=200,
        error_messages={"required": "Descreva o estado visível do aparelho."},
    )
    tecnico = forms.ModelChoiceField(
        label="Técnico responsável",
        queryset=User.objects.none(),
        required=False,
        empty_label="Definir depois",
    )
    data_prevista = forms.DateField(
        label="Entrega prevista",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = User.objects.filter(
            groups__name=TECNICO, is_active=True
        ).order_by("first_name", "username")

    def clean_numero_os(self):
        numero = self.cleaned_data["numero_os"]
        if OrdemServico.objects.filter(numero_os=numero).exists():
            raise forms.ValidationError("Já existe uma OS com este número.")
        return numero

    def clean_data_prevista(self):
        data = self.cleaned_data.get("data_prevista")
        if data and data < timezone.localdate():
            raise forms.ValidationError("A data prevista não pode ser anterior a hoje.")
        return data
