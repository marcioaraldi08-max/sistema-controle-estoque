from datetime import datetime
import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "chave-temporaria-apenas-desenvolvimento"
)
# Configurações básicas de segurança de sessão/cookie
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATABASE = os.environ.get("DATABASE_PATH", "estoque.db")


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL CHECK(preco >= 0),
            quantidade INTEGER NOT NULL CHECK(quantidade >= 0),
            quantidade_minima INTEGER NOT NULL CHECK(quantidade_minima >= 0)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id_movimentacao INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'saida')),
            quantidade INTEGER NOT NULL CHECK(quantidade > 0),
            data_movimentacao TEXT NOT NULL,
            FOREIGN KEY (id_produto) REFERENCES produtos (id_produto)
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.after_request
def aplicar_headers_seguranca(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@app.route("/")
def index():
    conn = get_db_connection()
    produtos = conn.execute(
        "SELECT * FROM produtos ORDER BY nome ASC"
    ).fetchall()

    movimentacoes = conn.execute("""
        SELECT m.id_movimentacao, p.nome AS produto_nome, m.tipo,
               m.quantidade, m.data_movimentacao
        FROM movimentacoes m
        JOIN produtos p ON m.id_produto = p.id_produto
        ORDER BY m.id_movimentacao DESC
        LIMIT 10
    """).fetchall()

    total_produtos = len(produtos)
    estoques_baixos = sum(
        1 for p in produtos
        if p["quantidade"] <= p["quantidade_minima"]
    )
    estoques_normais = total_produtos - estoques_baixos

    conn.close()

    return render_template(
        "index.html",
        produtos=produtos,
        movimentacoes=movimentacoes,
        total=total_produtos,
        normais=estoques_normais,
        baixos=estoques_baixos,
    )


@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form.get("nome", "").strip()

    try:
        preco = float(request.form.get("preco", ""))
        quantidade = int(request.form.get("quantidade", ""))
        quantidade_minima = int(request.form.get("quantidade_minima", ""))
    except ValueError:
        flash("Preencha preço e quantidades com valores válidos.", "error")
        return redirect(url_for("index"))

    if not nome or len(nome) > 100:
        flash("O nome do produto é obrigatório (máx. 100 caracteres).", "error")
        return redirect(url_for("index"))

    if preco < 0 or quantidade < 0 or quantidade_minima < 0:
        flash("Não são permitidos valores negativos.", "error")
        return redirect(url_for("index"))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO produtos
            (nome, preco, quantidade, quantidade_minima)
            VALUES (?, ?, ?, ?)
            """,
            (nome, preco, quantidade, quantidade_minima),
        )

        produto_id = cursor.lastrowid
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if quantidade > 0:
            cursor.execute(
                """
                INSERT INTO movimentacoes
                (id_produto, tipo, quantidade, data_movimentacao)
                VALUES (?, 'entrada', ?, ?)
                """,
                (produto_id, quantidade, data_atual),
            )

        conn.commit()
        flash("Produto cadastrado com sucesso!", "success")
    except sqlite3.Error:
        conn.rollback()
        flash("Erro ao salvar produto no banco de dados.", "error")
    finally:
        conn.close()

    return redirect(url_for("index"))


@app.route("/movimentar", methods=["POST"])
def movimentar():
    tipo = request.form.get("tipo", "").strip().lower()

    try:
        id_produto = int(request.form.get("id_produto", ""))
        quantidade = int(request.form.get("quantidade", ""))
    except ValueError:
        flash("Selecione um produto e informe uma quantidade válida.", "error")
        return redirect(url_for("index"))

    if tipo not in ("entrada", "saida"):
        flash("Tipo de movimentação inválido.", "error")
        return redirect(url_for("index"))

    if quantidade <= 0:
        flash("A quantidade movimentada deve ser maior que zero.", "error")
        return redirect(url_for("index"))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        produto = cursor.execute(
            "SELECT id_produto, nome, quantidade FROM produtos WHERE id_produto = ?",
            (id_produto,),
        ).fetchone()

        if not produto:
            flash("Produto não encontrado.", "error")
            return redirect(url_for("index"))

        saldo_atual = produto["quantidade"]

        if tipo == "saida" and quantidade > saldo_atual:
            flash(
                f"Estoque insuficiente para '{produto['nome']}'. Saldo atual: {saldo_atual}.",
                "error",
            )
            return redirect(url_for("index"))

        novo_saldo = (
            saldo_atual + quantidade if tipo == "entrada" else saldo_atual - quantidade
        )
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "UPDATE produtos SET quantidade = ? WHERE id_produto = ?",
            (novo_saldo, id_produto),
        )

        cursor.execute(
            """
            INSERT INTO movimentacoes
            (id_produto, tipo, quantidade, data_movimentacao)
            VALUES (?, ?, ?, ?)
            """,
            (id_produto, tipo, quantidade, data_atual),
        )

        conn.commit()
        acao = "Entrada" if tipo == "entrada" else "Saída"
        flash(f"{acao} de {quantidade} un. registrada para '{produto['nome']}'!", "success")
    except sqlite3.Error:
        conn.rollback()
        flash("Erro ao processar movimentação de estoque.", "error")
    finally:
        conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False)
