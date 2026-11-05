# TechFix, MVP de checklist de OS

Sistema web simples, complementar ao programa atual da TechFix Zona Leste
(assistência técnica de celulares, notebooks e videogames). Registra a ficha de
entrada do aparelho, o checklist de testes de saída e impede concluir uma OS
com teste pendente. Liga-se ao programa da loja só pelo número da OS
(4 a 8 dígitos). Não guarda CPF, telefone nem valores.

Status: em desenvolvimento. Projeto acadêmico, com dados fictícios.

## Tecnologias
Python, Django 5.2 LTS, SQLite.

## Como rodar
    python -m venv .venv
    source .venv/Scripts/activate      (Windows PowerShell: .venv\Scripts\activate)
    pip install -r requirements.txt
    cp .env.example .env               (e preencha as variáveis)
    python manage.py migrate
    python manage.py runserver

## Testes
    python manage.py test

## Arquitetura
Monolito em camadas (MVT): Models (dados), Views (regras) e Templates (telas).
EOFpip freeze > requirements.txt

cat > README.md << 'EOF'
# TechFix, MVP de checklist de OS

Sistema web simples, complementar ao programa atual da TechFix Zona Leste
(assistência técnica de celulares, notebooks e videogames). Registra a ficha de
entrada do aparelho, o checklist de testes de saída e impede concluir uma OS
com teste pendente. Liga-se ao programa da loja só pelo número da OS
(4 a 8 dígitos). Não guarda CPF, telefone nem valores.

Status: em desenvolvimento. Projeto acadêmico, com dados fictícios.

## Tecnologias
Python, Django 5.2 LTS, SQLite.

## Como rodar
    python -m venv .venv
    source .venv/Scripts/activate      (Windows PowerShell: .venv\Scripts\activate)
    pip install -r requirements.txt
    cp .env.example .env               (e preencha as variáveis)
    python manage.py migrate
    python manage.py runserver

## Testes
    python manage.py test

## Arquitetura
Monolito em camadas (MVT): Models (dados), Views (regras) e Templates (telas).
