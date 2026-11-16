
import sqlite3

import pytest
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    banco_teste = tmp_path / "estoque_teste.db"

    monkeypatch.setattr(
        app_module,
        "DATABASE",
        str(banco_teste)
    )

    app_module.init_db()

    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")

    assert response.status_code == 200


def test_cadastrar_produto(client):
    response = client.post(
        "/cadastrar",
        data={
            "nome": "Café 500g",
            "preco": "18.90",
            "quantidade": "20",
            "quantidade_minima": "5",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = sqlite3.connect(app_module.DATABASE)
    produto = conn.execute(
        "SELECT nome, preco, quantidade FROM produtos"
    ).fetchone()
    movimentacao = conn.execute(
        "SELECT tipo, quantidade FROM movimentacoes"
    ).fetchone()
    conn.close()

    assert produto == ("Café 500g", 18.9, 20)
    assert movimentacao == ("entrada", 20)


def test_rejeitar_preco_invalido(client):
    response = client.post(
        "/cadastrar",
        data={
            "nome": "Arroz 5kg",
            "preco": "abc",
            "quantidade": "10",
            "quantidade_minima": "2",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = sqlite3.connect(app_module.DATABASE)
    total = conn.execute(
        "SELECT COUNT(*) FROM produtos"
    ).fetchone()[0]
    conn.close()

    assert total == 0


def test_rejeitar_quantidade_negativa(client):
    response = client.post(
        "/cadastrar",
        data={
            "nome": "Feijão 1kg",
            "preco": "8.90",
            "quantidade": "-5",
            "quantidade_minima": "2",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = sqlite3.connect(app_module.DATABASE)
    total = conn.execute(
        "SELECT COUNT(*) FROM produtos"
    ).fetchone()[0]
    conn.close()

    assert total == 0
