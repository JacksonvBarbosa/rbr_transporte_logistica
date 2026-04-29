from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from rbr_transporte_logistica.core.database import Base, create_db_engine
from rbr_transporte_logistica.repositories.cliente_repository import ClienteRepository


def make_session():
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_criar_e_listar_cliente():
    session = make_session()
    repository = ClienteRepository(session)

    criado = repository.criar(
        {
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "cpf_cnpj": "12345678900",
            "ativo": True,
        }
    )

    clientes = repository.listar()

    assert criado.id is not None
    assert [cliente.nome for cliente in clientes] == ["Cliente Teste"]


def test_listar_clientes_filtra_inativos():
    session = make_session()
    repository = ClienteRepository(session)

    ativo = repository.criar({"nome": "Ativo", "ativo": True})
    inativo = repository.criar({"nome": "Inativo", "ativo": False})

    clientes_ativos = repository.listar()
    todos = repository.listar(apenas_ativos=False)

    assert [cliente.id for cliente in clientes_ativos] == [ativo.id]
    assert {cliente.id for cliente in todos} == {ativo.id, inativo.id}


def test_desativar_cliente_por_atualizacao():
    session = make_session()
    repository = ClienteRepository(session)

    cliente = repository.criar({"nome": "Cliente Toggle", "ativo": True})
    atualizado = repository.atualizar(cliente.id, {"ativo": False})

    assert atualizado is not None
    assert atualizado.ativo is False
    assert repository.listar() == []
