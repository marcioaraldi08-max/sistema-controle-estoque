from datetime import datetime
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.secret_key = "chave-secreta-mercadinho-fsg"

DATABASE = "estoque.db"


def get_db_connection():
  conn = sqlite3.connect(DATABASE)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  # Tabela de Produtos conforme planejado no projeto
  conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL CHECK(preco >= 0),
            quantidade INTEGER NOT NULL CHECK(quantidade >= 0),
            quantidade_minima INTEGER NOT NULL CHECK(quantidade_minima >= 0)
        )
    """)
  # Tabela de Movimentações (Entradas e Saídas)
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


# Inicializa o banco ao iniciar
init_db()


@app.route("/")
def index():
  conn = get_db_connection()
  produtos = conn.execute("SELECT * FROM produtos").fetchall()

  # Calcula alertas de estoque baixo (RF05)
  total_produtos = len(produtos)
  estoques_baixos = 0
  for p in produtos:
    if p["quantidade"] <= p["quantidade_minima"]:
      estoques_baixos += 1

  estoques_normais = total_produtos - estoques_baixos
  conn.close()

  # Template HTML integrado simples para exibição do MVP
  html_code = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Controle de Estoque - Mercadinho</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-primary shadow-sm">
            <div class="container-fluid">
                <span class="navbar-brand mb-0 h1">Controle de Estoque — Mercadinho de Bairro</span>
            </div>
        </nav>
        <div class="container my-4">
            <div class="row text-center mb-4">
                <div class="col-md-4">
                    <div class="card shadow-sm p-3">
                        <h5>Total de Produtos</h5>
                        <h3>{{ total }}</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card shadow-sm p-3 border-success">
                        <h5>Estoque Normal</h5>
                        <h3 class="text-success">{{ normais }}</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card shadow-sm p-3 border-danger">
                        <h5>Estoque Baixo</h5>
                        <h3 class="text-danger">{{ baixos }}</h3>
                    </div>
                </div>
            </div>

            <div class="card shadow-sm p-4 mb-4">
                <h4>Cadastrar Novo Produto</h4>
                <form action="/cadastrar" method="POST" class="row g-3 mt-2">
                    <div class="col-md-4">
                        <label class="form-label">Nome do Produto</label>
                        <input type="text" name="nome" class="form-control" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Preço (R$)</label>
                        <input type="number" step="0.01" name="preco" class="form-control" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Qtd Inicial</label>
                        <input type="number" name="quantidade" class="form-control" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Qtd Mínima</label>
                        <input type="number" name="quantidade_minima" class="form-control" required>
                    </div>
                    <div class="col-12">
                        <button type="submit" class="btn btn-primary">Cadastrar Produto</button>
                    </div>
                </form>
            </div>

            <div class="card shadow-sm p-4">
                <h4>Lista de Produtos em Estoque</h4>
                <table class="table table-striped mt-3">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nome</th>
                            <th>Preço</th>
                            <th>Quantidade</th>
                            <th>Mínimo</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in produtos %}
                        <tr>
                            <td>{{ p.id_produto }}</td>
                            <td>{{ p.nome }}</td>
                            <td>R$ {{ "%.2f"|format(p.preco) }}</td>
                            <td>{{ p.quantidade }}</td>
                            <td>{{ p.quantidade_minima }}</td>
                            <td>
                                {% if p.quantidade <= p.quantidade_minima %}
                                    <span class="badge bg-danger">Estoque Baixo</span>
                                {% else %}
                                    <span class="badge bg-success">Em Estoque</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center">Nenhum produto cadastrado ainda.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
  return render_template_string(
      html_code,
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
      "INSERT INTO produtos (nome, preco, quantidade, quantidade_minima)"
      " VALUES (?, ?, ?, ?)",
      (nome, preco, quantidade, quantidade_minima),
  )
  produto_id = cursor.lastrowid

  # Registra a movimentação inicial de entrada
  data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cursor.execute(
      "INSERT INTO movimentacoes (id_produto, tipo, quantidade,"
      " data_movimentacao) VALUES (?, 'entrada', ?, ?)",
      (produto_id, quantidade, data_atual),
  )

  conn.commit()
  conn.close()
  return redirect(url_for("index"))


if __name__ == "__main__":
  app.run(debug=True)
