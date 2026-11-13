from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from conferencia.models import TesteModelo

TESTES = {
    "celular": ["Tela", "Touch", "Câmeras", "Carga", "Conexões"],
    "notebook": ["Tela", "Teclado", "Fonte", "Carga", "Peças fixadas"],
    "videogame": ["Imagem", "Controles", "Carga", "Conexões"],
    "outro": ["Funcionamento geral"],
}


class Command(BaseCommand):
    help = "Cria os grupos Atendente e Tecnico e os testes padrão por tipo de aparelho."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Cria usuários de demonstração.")
        parser.add_argument("--senha", help="Senha dos usuários de demonstração (só com --demo).")

    def handle(self, *args, **opcoes):
        for nome in ("Atendente", "Tecnico"):
            Group.objects.get_or_create(name=nome)
        for tipo, nomes in TESTES.items():
            for ordem, nome in enumerate(nomes, start=1):
                TesteModelo.objects.get_or_create(
                    tipo_aparelho=tipo, nome_teste=nome, defaults={"ordem": ordem}
                )
        if opcoes["demo"]:
            if not opcoes["senha"]:
                raise CommandError("Informe --senha para criar os usuários de demonstração.")
            User = get_user_model()
            for usuario, nome, grupo in (
                ("atendente_demo", "Atendente Demo", "Atendente"),
                ("tecnico1", "Técnico 1", "Tecnico"),
            ):
                if not User.objects.filter(username=usuario).exists():
                    novo = User.objects.create_user(usuario, password=opcoes["senha"], first_name=nome)
                    novo.groups.add(Group.objects.get(name=grupo))
        self.stdout.write("Dados iniciais carregados.")
