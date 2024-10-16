from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(
        dbname="tcc_mlul",
        user="guilherme",
        password="UHnP3RoMsq3qcWMJVPHQ7LtFq4zbD9yQ",
        host="dpg-crvgsa08fa8c739a75l0-a.oregon-postgres.render.com",
        port="5432"
    )

class RFIDData(BaseModel):
    rfid: str

@app.post("/sensor_data/")
def process_rfid(data: RFIDData):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Verificar se o RFID corresponde a algum produto
        cursor.execute("SELECT nome_produto FROM produtos WHERE rfid = %s", (data.rfid,))
        produto = cursor.fetchone()

        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto não encontrado para o RFID {data.rfid}")

        nome_produto = produto[0]
        print(f"Produto encontrado: {nome_produto}")

        # Buscar o primeiro pedido correspondente ao nome do produto
        cursor.execute("""
            SELECT id, nome, nome_produto, preco, quantidade, hora 
            FROM pedidos WHERE nome_produto = %s ORDER BY id ASC LIMIT 1
        """, (nome_produto,))
        pedido = cursor.fetchone()

        if not pedido:
            raise HTTPException(status_code=404, detail=f"Nenhum pedido encontrado para o produto {nome_produto}")

        pedido_id, nome, nome_produto, preco, quantidade, hora = pedido
        print(f"Pedido encontrado: ID={pedido_id}, Nome={nome}, Produto={nome_produto}, Preço={preco}, Quantidade={quantidade}")

        if quantidade > 1:
            # Se a quantidade for maior que 1, apenas reduz a quantidade em 1
            cursor.execute("""
                UPDATE pedidos SET quantidade = quantidade - 1 WHERE id = %s
            """, (pedido_id,))
            print(f"Quantidade reduzida para o pedido ID={pedido_id}. Nova quantidade: {quantidade - 1}")
        else:
            # Se a quantidade for 1, move o pedido para 'pedidos_feitos' e remove da tabela 'pedidos'
            cursor.execute("""
                INSERT INTO pedidos_feitos (nome, nome_produto, preco, quantidade, hora)
                VALUES (%s, %s, %s, %s, %s)
            """, (nome, nome_produto, preco, quantidade, hora))
            print(f"Pedido movido para pedidos_feitos: ID={pedido_id}, Produto={nome_produto}")
            
            cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
            print(f"Pedido removido da tabela pedidos: ID={pedido_id}")

        connection.commit()
        return {"message": f"Pedido com o produto '{nome_produto}' processado com sucesso"}
    
    except Exception as e:
        connection.rollback()
        print(f"Erro ao mover pedidos: {e}")  # Log do erro específico
        raise HTTPException(status_code=500, detail=f"Erro ao mover pedidos no banco de dados: {str(e)}")
    
    finally:
        cursor.close()
        connection.close()

# Endpoint de ping
@app.get("/ping")
def ping():
    return {"message": "API está funcionando!"}
