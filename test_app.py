from app import app, init_db
import pytest


@pytest.fixture
def client():
  app.config["TESTING"] = True
  init_db()
  with app.test_client() as client:
    yield client


def test_index_page(client):
  response = client.get("/")
  assert response.status_code == 200
  assert b"Controle de Estoque" in response.data


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
  assert b"Café 500g" in response.data
