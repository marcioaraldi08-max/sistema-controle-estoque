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


def test_index_page_e_headers_seguranca(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"


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
    total = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
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
    total = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    conn.close()

    assert total == 0


def test_movimentar_entrada_e_saida(client):
    client.post(
        "/cadastrar",
        data={
            "nome": "Leite Integral 1L",
            "preco": "5.50",
            "quantidade": "10",
            "quantidade_minima": "3",
        },
    )

    # Registrar entrada de 5 unidades (saldo deve ir para 15)
    resp_entrada = client.post(
        "/movimentar",
        data={
            "id_produto": "1",
            "tipo": "entrada",
            "quantidade": "5",
        },
        follow_redirects=True,
    )
    assert resp_entrada.status_code == 200

    # Registrar saída de 4 unidades (saldo deve ir para 11)
    resp_saida = client.post(
        "/movimentar",
        data={
            "id_produto": "1",
            "tipo": "saida",
            "quantidade": "4",
        },
        follow_redirects=True,
    )
    assert resp_saida.status_code == 200

    conn = sqlite3.connect(app_module.DATABASE)
    saldo = conn.execute(
        "SELECT quantidade FROM produtos WHERE id_produto = 1"
    ).fetchone()[0]
    total_movs = conn.execute(
        "SELECT COUNT(*) FROM movimentacoes WHERE id_produto = 1"
    ).fetchone()[0]
    conn.close()

    assert saldo == 11
    assert total_movs == 3  # 1 cadastro inicial + 1 entrada + 1 saída


def test_bloquear_saida_maior_que_saldo(client):
    client.post(
        "/cadastrar",
        data={
            "nome": "Açúcar 1kg",
            "preco": "4.80",
            "quantidade": "5",
            "quantidade_minima": "2",
        },
    )

    # Tentar dar saída de 8 unidades tendo apenas 5
    response = client.post(
        "/movimentar",
        data={
            "id_produto": "1",
            "tipo": "saida",
            "quantidade": "8",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = sqlite3.connect(app_module.DATABASE)
    saldo = conn.execute(
        "SELECT quantidade FROM produtos WHERE id_produto = 1"
    ).fetchone()[0]
    conn.close()

    assert saldo == 5  # Saldo deve permanecer intacto
