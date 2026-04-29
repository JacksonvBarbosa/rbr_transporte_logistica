from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from rbr_transporte_logistica.core.models import Cliente


class ClienteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def criar(self, dados: dict) -> Cliente:
        cliente = Cliente(**dados)
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def listar(self, apenas_ativos: bool = True) -> list[Cliente]:
        stmt = select(Cliente).order_by(Cliente.nome)
        if apenas_ativos:
            stmt = stmt.where(Cliente.ativo.is_(True))
        return list(self.db.scalars(stmt).all())

    def buscar_por_id(self, id: int) -> Cliente | None:
        return self.db.get(Cliente, id)

    def atualizar(self, id: int, dados: dict) -> Cliente | None:
        cliente = self.buscar_por_id(id)
        if not cliente:
            return None
        for key, value in dados.items():
            setattr(cliente, key, value)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def deletar(self, id: int) -> bool:
        cliente = self.buscar_por_id(id)
        if not cliente:
            return False
        self.db.delete(cliente)
        self.db.commit()
        return True
