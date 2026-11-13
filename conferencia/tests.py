from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import NovaOSForm
from .models import (
    ConclusaoBloqueada,
    FichaEntrada,
    ItemChecklist,
    OrdemServico,
)
from .services import criar_os_com_ficha

User = get_user_model()
SENHA_TESTE = "senha-so-para-teste-123"


class BaseTeste(TestCase):
    """Cria grupos, testes padrão e dois usuários fictícios."""

    def setUp(self):
        call_command("carregar_dados_iniciais")
        self.atendente = User.objects.create_user("atendente", password=SENHA_TESTE)
        self.atendente.groups.add(Group.objects.get(name="Atendente"))
        self.tecnico = User.objects.create_user("tecnico", password=SENHA_TESTE)
        self.tecnico.groups.add(Group.objects.get(name="Tecnico"))

    def nova_ordem(self, numero="48213", tipo="celular", acessorios="carregador e capa", **extra):
        return criar_os_com_ficha(
            numero_os=numero,
            tipo_aparelho=tipo,
            descricao_curta="Celular de teste",
            acessorios_recebidos=acessorios,
            estado_visivel="tela trincada no canto",
            usuario=self.atendente,
            **extra,
        )

    def dados_post(self, **mudancas):
        dados = {
            "numero_os": "48213",
            "tipo_aparelho": "celular",
            "descricao_curta": "Celular de teste",
            "acessorios_recebidos": "carregador e capa",
            "estado_visivel": "tela trincada no canto",
            "tecnico": "",
            "data_prevista": "",
        }
        dados.update(mudancas)
        return dados


# ---------------- Testes unitários (regras e modelos) ----------------
class RegrasDeNegocioTest(BaseTeste):
    def test_numero_os_aceita_4_a_8_digitos(self):
        for numero in ("4821", "48213", "12345678"):
            OrdemServico(numero_os=numero, tipo_aparelho="celular", descricao_curta="x").full_clean()

    def test_numero_os_recusa_formatos_invalidos(self):
        for numero in ("123", "123456789", "12a45", "1234\n", "' OR 1=1 --"):
            with self.assertRaises(ValidationError, msg=numero):
                OrdemServico(numero_os=numero, tipo_aparelho="celular", descricao_curta="x").full_clean()

    def test_criar_os_gera_ficha_e_checklist_do_tipo(self):
        ordem = self.nova_ordem()
        self.assertEqual(ordem.status, OrdemServico.RECEBIDO)
        self.assertTrue(FichaEntrada.objects.filter(ordem_servico=ordem).exists())
        self.assertEqual(ordem.itens.count(), 5)
        self.assertFalse(ordem.itens.exclude(resultado=ItemChecklist.PENDENTE).exists())

    def test_checklist_de_notebook_tem_os_testes_de_notebook(self):
        ordem = self.nova_ordem(numero="55555", tipo="notebook")
        nomes = [i.teste.nome_teste for i in ordem.itens.all()]
        self.assertIn("Fonte", nomes)
        self.assertNotIn("Touch", nomes)

    def test_numero_da_os_nao_se_repete(self):
        self.nova_ordem()
        with self.assertRaises(ValidationError):
            self.nova_ordem()

    def test_so_tecnico_pode_ser_responsavel(self):
        with self.assertRaises(ValidationError):
            self.nova_ordem(tecnico=self.atendente)

    def test_conclusao_bloqueada_com_item_pendente(self):
        ordem = self.nova_ordem()
        ordem.status = OrdemServico.EM_REPARO
        ordem.save()
        for item in list(ordem.itens.all())[:2]:
            item.resultado = ItemChecklist.APROVADO
            item.save()
        with self.assertRaises(ConclusaoBloqueada) as contexto:
            ordem.concluir()
        self.assertEqual(len(contexto.exception.pendentes), 3)
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.EM_REPARO)

    def test_conclusao_aceita_aprovado_e_nao_se_aplica(self):
        ordem = self.nova_ordem()
        ordem.status = OrdemServico.EM_REPARO
        ordem.save()
        itens = list(ordem.itens.all())
        for item in itens[:-1]:
            item.resultado = ItemChecklist.APROVADO
            item.save()
        itens[-1].resultado = ItemChecklist.NAO_SE_APLICA
        itens[-1].save()
        ordem.concluir()
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.PRONTO)
        self.assertIsNotNone(ordem.concluida_em)

    def test_conclusao_exige_status_em_reparo(self):
        ordem = self.nova_ordem()
        with self.assertRaises(ValidationError):
            ordem.concluir()

    def test_formulario_recusa_data_prevista_no_passado(self):
        passado = (timezone.localdate() - timedelta(days=1)).isoformat()
        form = NovaOSForm(data=self.dados_post(data_prevista=passado))
        self.assertFalse(form.is_valid())
        self.assertIn("data_prevista", form.errors)

    def test_senha_guardada_com_hash_pbkdf2(self):
        self.assertTrue(self.atendente.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn(SENHA_TESTE, self.atendente.password)


# ---------------- Testes de integração (telas, banco e permissões) ----------------
class TelasEPermissoesTest(BaseTeste):
    def test_visitante_vai_para_o_login(self):
        for url in (reverse("inicio"), reverse("nova_os"), reverse("detalhe", args=["48213"])):
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 302)
            self.assertIn("/entrar/", resposta.url)

    def test_login_valido_e_invalido(self):
        recusa = self.client.post(reverse("login"), {"username": "atendente", "password": "errada"})
        self.assertEqual(recusa.status_code, 200)
        self.assertFalse(recusa.wsgi_request.user.is_authenticated)
        aceita = self.client.post(reverse("login"), {"username": "atendente", "password": SENHA_TESTE})
        self.assertEqual(aceita.status_code, 302)

    def test_atendente_cria_os_pela_tela(self):
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse("nova_os"), self.dados_post())
        self.assertRedirects(resposta, reverse("detalhe", args=["48213"]))
        ordem = OrdemServico.objects.get(numero_os="48213")
        self.assertEqual(ordem.itens.count(), 5)
        self.assertTrue(hasattr(ordem, "ficha"))

    def test_tecnico_nao_cria_os(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(reverse("nova_os")).status_code, 403)
        self.assertEqual(self.client.post(reverse("nova_os"), self.dados_post()).status_code, 403)
        self.assertFalse(OrdemServico.objects.exists())

    def test_acessorios_obrigatorios_com_mensagem_clara(self):
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse("nova_os"), self.dados_post(acessorios_recebidos=""))
        self.assertEqual(resposta.status_code, 200)
        self.assertFormError(
            resposta.context["form"],
            "acessorios_recebidos",
            ['Informe os acessórios recebidos ou escreva "nenhum".'],
        )
        self.assertFalse(OrdemServico.objects.exists())

    def test_numero_repetido_e_recusado_na_tela(self):
        self.nova_ordem()
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse("nova_os"), self.dados_post())
        self.assertFormError(resposta.context["form"], "numero_os", ["Já existe uma OS com este número."])

    def test_busca_com_numero_valido_leva_a_os(self):
        self.nova_ordem()
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse("inicio"), {"numero_os": "48213"})
        self.assertRedirects(resposta, reverse("detalhe", args=["48213"]))

    def test_busca_de_numero_inexistente(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse("inicio"), {"numero_os": "99999"})
        self.assertContains(resposta, "OS não encontrada")

    def test_busca_recusa_formato_invalido_e_tentativa_de_injecao(self):
        self.nova_ordem()
        self.client.force_login(self.atendente)
        for texto in ("123", "' OR 1=1 --"):
            resposta = self.client.get(reverse("inicio"), {"numero_os": texto})
            self.assertEqual(resposta.status_code, 200)
            self.assertContains(resposta, "O número da OS deve ter de 4 a 8 dígitos")

    def test_atendente_nao_marca_checklist(self):
        ordem = self.nova_ordem()
        ordem.status = OrdemServico.EM_REPARO
        ordem.save()
        item = ordem.itens.first()
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse("marcar_item", args=[item.pk, "aprovado"]))
        self.assertEqual(resposta.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.resultado, ItemChecklist.PENDENTE)

    def test_tecnico_inicia_reparo_e_marca_item_com_autor_e_hora(self):
        ordem = self.nova_ordem()
        self.client.force_login(self.tecnico)
        self.client.post(reverse("iniciar_reparo", args=["48213"]))
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.EM_REPARO)
        item = ordem.itens.first()
        self.client.post(reverse("marcar_item", args=[item.pk, "aprovado"]))
        item.refresh_from_db()
        self.assertEqual(item.resultado, ItemChecklist.APROVADO)
        self.assertEqual(item.marcado_por, self.tecnico)
        self.assertIsNotNone(item.marcado_em)

    def test_resultado_invalido_na_url_da_404(self):
        ordem = self.nova_ordem()
        self.client.force_login(self.tecnico)
        item = ordem.itens.first()
        resposta = self.client.post(reverse("marcar_item", args=[item.pk, "reprovado"]))
        self.assertEqual(resposta.status_code, 404)

    def test_concluir_com_pendencia_mostra_alerta_e_nao_muda_status(self):
        ordem = self.nova_ordem()
        ordem.status = OrdemServico.EM_REPARO
        ordem.save()
        self.client.force_login(self.tecnico)
        resposta = self.client.post(reverse("concluir", args=["48213"]))
        self.assertContains(resposta, "Não é possível concluir")
        self.assertContains(resposta, "Câmeras")
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.EM_REPARO)

    def test_concluir_sem_pendencia_deixa_a_os_pronta(self):
        ordem = self.nova_ordem()
        ordem.status = OrdemServico.EM_REPARO
        ordem.save()
        ordem.itens.update(resultado=ItemChecklist.APROVADO)
        self.client.force_login(self.tecnico)
        resposta = self.client.post(reverse("concluir", args=["48213"]))
        self.assertContains(resposta, "pronta")
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.PRONTO)

    def test_atendente_registra_cliente_avisado_so_depois_de_pronta(self):
        ordem = self.nova_ordem()
        self.client.force_login(self.atendente)
        self.client.post(reverse("avisar_cliente", args=["48213"]))
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.RECEBIDO)
        ordem.status = OrdemServico.PRONTO
        ordem.save()
        self.client.post(reverse("avisar_cliente", args=["48213"]))
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.CLIENTE_AVISADO)

    def test_texto_digitado_com_script_aparece_escapado(self):
        self.nova_ordem(acessorios="<script>alert(1)</script>")
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse("detalhe", args=["48213"]))
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.assertContains(resposta, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_painel_de_carga_conta_so_os_abertas(self):
        for numero in ("11111", "22222", "33333"):
            self.nova_ordem(numero=numero, tecnico=self.tecnico)
        pronta = self.nova_ordem(numero="44444", tecnico=self.tecnico)
        pronta.status = OrdemServico.PRONTO
        pronta.save()
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse("inicio"))
        linha = [t for t in resposta.context["carga"] if t.pk == self.tecnico.pk][0]
        self.assertEqual(linha.em_aberto, 3)

    def test_pagina_de_os_inexistente_da_404(self):
        self.client.force_login(self.atendente)
        self.assertEqual(self.client.get(reverse("detalhe", args=["99999"])).status_code, 404)

    def test_comando_de_dados_iniciais_e_idempotente(self):
        total = self.nova_ordem().itens.count()
        call_command("carregar_dados_iniciais")
        call_command("carregar_dados_iniciais")
        self.assertEqual(self.nova_ordem(numero="77777").itens.count(), total)
