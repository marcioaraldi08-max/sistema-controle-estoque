from datetime import datetime
import os
import sqlite3
from datetime import datetime
import sqlite3
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "chave-temporaria-apenas-desenvolvimento"
)

DATABASE = "estoque.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
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


@app.route("/")
def index():
    conn = get_db_connection()
    produtos = conn.execute("SELECT * FROM produtos").fetchall()

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
        total=total_produtos,
        normais=estoques_normais,
        baixos=estoques_baixos,
    )


@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form["nome"]
    preco = float(request.form["preco"])
    quantidade = int(request.form["quantidade"])
    quantidade_minima = int(request.form["quantidade_minima"])

    conn = get_db_connection()
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

    cursor.execute(
        """
        INSERT INTO movimentacoes
        (id_produto, tipo, quantidade, data_movimentacao)
        VALUES (?, 'entrada', ?, ?)
        """,
        (produto_id, quantidade, data_atual),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
app.run(debug=False)
