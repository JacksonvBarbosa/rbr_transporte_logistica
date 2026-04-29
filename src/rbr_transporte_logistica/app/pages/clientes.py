from __future__ import annotations

import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_cliente_repository
from rbr_transporte_logistica.app.theme import apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session


def render() -> None:
    apply_theme()
    sidebar_nav("Clientes")
    st.header("Clientes")

    with db_session() as session:
        cliente_repo = build_cliente_repository(session)

        with st.expander("➕ Novo cliente", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome *", key="cliente_nome")
            email = col2.text_input("Email", key="cliente_email")
            col3, col4 = st.columns(2)
            telefone = col3.text_input("Telefone", key="cliente_telefone")
            cpf_cnpj = col4.text_input("CPF/CNPJ", key="cliente_cpf_cnpj")
            endereco = st.text_input("Endereco", key="cliente_endereco")
            col5, col6 = st.columns(2)
            cidade = col5.text_input("Cidade", key="cliente_cidade")
            uf = col6.text_input("UF", key="cliente_uf", max_chars=2)

            if st.button("Cadastrar cliente", key="cadastrar_cliente", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome do cliente.")
                else:
                    try:
                        cliente_repo.criar(
                            {
                                "nome": nome.strip(),
                                "email": email.strip() or None,
                                "telefone": telefone.strip() or None,
                                "cpf_cnpj": cpf_cnpj.strip() or None,
                                "endereco": endereco.strip() or None,
                                "cidade": cidade.strip() or None,
                                "uf": uf.strip().upper() or None,
                                "ativo": True,
                            }
                        )
                        st.success("Cliente cadastrado com sucesso.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Nao foi possivel cadastrar o cliente: {exc}")

        st.markdown("### Clientes cadastrados")
        clientes = cliente_repo.listar(apenas_ativos=False)
        if not clientes:
            st.info("Nenhum cliente cadastrado.")
            return

        for cliente in clientes:
            status = "Ativo" if cliente.ativo else "Inativo"
            titulo = f"{cliente.nome} - {cliente.cidade or '-'} / {cliente.uf or '-'} - {status}"
            with st.expander(titulo, expanded=False):
                col1, col2 = st.columns(2)
                edit_nome = col1.text_input("Nome *", value=cliente.nome, key=f"edit_nome_{cliente.id}")
                edit_email = col2.text_input("Email", value=cliente.email or "", key=f"edit_email_{cliente.id}")
                col3, col4 = st.columns(2)
                edit_telefone = col3.text_input("Telefone", value=cliente.telefone or "",
                                                key=f"edit_telefone_{cliente.id}")
                edit_cpf_cnpj = col4.text_input("CPF/CNPJ", value=cliente.cpf_cnpj or "",
                                                key=f"edit_cpf_cnpj_{cliente.id}")
                edit_endereco = st.text_input("Endereco", value=cliente.endereco or "",
                                              key=f"edit_endereco_{cliente.id}")
                col5, col6 = st.columns(2)
                edit_cidade = col5.text_input("Cidade", value=cliente.cidade or "", key=f"edit_cidade_{cliente.id}")
                edit_uf = col6.text_input("UF", value=cliente.uf or "", key=f"edit_uf_{cliente.id}", max_chars=2)
                ativo = st.toggle("Cliente ativo", value=cliente.ativo, key=f"ativo_cliente_{cliente.id}")
                action_cols = st.columns(2)
                if action_cols[0].button("Salvar alteracoes", key=f"salvar_cliente_{cliente.id}", type="primary"):
                    if not edit_nome.strip():
                        st.error("Informe o nome do cliente.")
                    else:
                        try:
                            cliente_repo.atualizar(
                                cliente.id,
                                {
                                    "nome": edit_nome.strip(),
                                    "email": edit_email.strip() or None,
                                    "telefone": edit_telefone.strip() or None,
                                    "cpf_cnpj": edit_cpf_cnpj.strip() or None,
                                    "endereco": edit_endereco.strip() or None,
                                    "cidade": edit_cidade.strip() or None,
                                    "uf": edit_uf.strip().upper() or None,
                                    "ativo": ativo,
                                },
                            )
                            st.success("Cliente atualizado.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Nao foi possivel atualizar o cliente: {exc}")
                if action_cols[1].button(
                    "Desativar" if cliente.ativo else "Ativar",
                    key=f"toggle_cliente_{cliente.id}",
                ):
                    try:
                        cliente_repo.atualizar(cliente.id, {"ativo": not cliente.ativo})
                        st.success("Status do cliente atualizado.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Nao foi possivel atualizar o status: {exc}")
