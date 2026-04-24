# Frete System

Sistema de calculo de frete para operacoes logisticas com cadastro de parceiros, ETL de arquivos, simulacao automatica por distancia, roteirizacao multi-trecho, mapa e geracao de orcamentos.

## Principais recursos

- CRUD completo de parceiros com ativacao, desativacao e geolocalizacao automatica
- CRUD completo de regras de frete com UX por formulario
- Simulacao com melhor preco e melhor prazo
- Distancia automatica entre origem e destino
- Roteirizacao multi-partner com composicao por trechos
- Visualizacao geografica em mapa com destaque de parceiros selecionados
- Exportacao de orcamentos em Excel e PDF
- Arquitetura modular com SQLAlchemy, Alembic e servicos desacoplados

## Tecnologias

- Python 3.11+
- Poetry
- PostgreSQL
- SQLAlchemy + Alembic
- Pandas
- Streamlit
- Folium
- ReportLab
- Geopy
- Pytest

## Como executar

### 1. Instalar dependencias

```bash
poetry install
```

### 2. Configurar ambiente

Defina a variavel `DATABASE_URL`. Exemplo:

```bash
postgresql+psycopg://postgres:postgres@localhost:5432/frete_system
```

Se a variavel nao for definida, o sistema usa esse valor padrao.

### 3. Aplicar migrations

```bash
poetry run alembic upgrade head
```

### 4. Executar a aplicacao

```bash
poetry run streamlit run app/main.py
```

## Fluxo principal

1. Cadastre parceiros com cidade e UF. O sistema busca latitude e longitude automaticamente.
2. Configure regras `LINEAR`, `FIXED` ou `TIERED` sem editar JSON manualmente.
3. Informe origem e destino na simulacao para calcular a distancia automatica.
4. Compare parceiros, selecione uma sequencia de atendimento e monte a rota multi-trecho.
5. Gere o orcamento final com impostos, margem e taxas adicionais.

## Estrutura

```text
frete_system/
├── app/
├── src/rbr_transporte_logistica/
├── tests/
└── alembic/
```

## Regras de frete

- `LINEAR`: `base_price + (km * price_per_km)`
- `FIXED`: usa `fixed_price`
- `TIERED`: encontra a primeira faixa compativel por km

## ETL

Formatos suportados:

- CSV
- XLSX
- PDF via `pdfplumber`

Colunas normalizadas:

- `partner`
- `city`
- `state`
- `price`
- `km`

## Testes

```bash
poetry run pytest
```

## Lint e formatacao

```bash
poetry run black .
poetry run flake8 .
```
