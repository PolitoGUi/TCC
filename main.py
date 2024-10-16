from flask import Flask, render_template, redirect, request, flash, session
import psycopg2
from psycopg2 import sql
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import uuid

    

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'admin'

def get_db_connection():
    conn_str = {
        'dbname': "tcc_wt2c",
        'user': "guilherme",
        'password': "ArRqQLQVOtJcdPs8DZLVmGWHxZy2ZJR6",
        'host': "dpg-crb3dsjtq21c73cf85rg-a.oregon-postgres.render.com",
        'port': "5432"
    }
    return psycopg2.connect(**conn_str)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login_adm')
def login_adm():
    return render_template('login_admin.html')

@app.route('/cliente')
def login_cliente():
    return render_template('login_cliente.html')

@app.route('/cd')
def cadastro():
    return render_template('cadastro.html')

@app.route('/compras')
def compras():
    return render_template('compras.html')

@app.route('/compras_realizadas')
def compras_realizadas():
    return render_template('compra_realizada.html')

from flask import render_template, request, session, redirect, flash
import psycopg2
from decimal import Decimal
from datetime import datetime

@app.route('/compra_realizada', methods=['POST'])
def compra_realizada():
    # Obter dados do formulário
    product_name = request.form.get('product_name')
    product_price = request.form.get('product_price')

    # Garantir que o preço seja um Decimal
    if product_price:
        product_price = Decimal(product_price.replace(',', '.'))
    else:
        product_price = Decimal('0.00')

    # Verificar se a quantidade foi fornecida, caso contrário, definir como 1
    quantidade = request.form.get('quantidade')
    if quantidade:
        quantidade = int(quantidade)
    else:
        quantidade = 1  # Valor padrão

    # Calcular o total
    total = product_price * quantidade

    # Obter e-mail do usuário da sessão
    user_email = session.get('username', None)

    # Validação dos dados
    if not product_name or not product_price or not user_email:
        return redirect('/compras')

    # Gerar o grupo do pedido baseado na data e hora
    pedido_grupo = datetime.now().strftime('%Y%m%d%H%M%S')

    conn = None
    cursor = None

    try:
        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter o nome do usuário a partir do e-mail
        cursor.execute("SELECT nome FROM usuarios WHERE email = %s", (user_email,))
        user_name_row = cursor.fetchone()
        if user_name_row:
            user_name = user_name_row[0]
        else:
            return redirect('/compras')

        # Inserir o pedido na tabela
        insert_query = """
            INSERT INTO pedidos (nome, nome_produto, preco, quantidade, hora, pedido_grupo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            user_name, 
            product_name, 
            product_price, 
            quantidade, 
            datetime.now(), 
            pedido_grupo
        ))

        # Atualizar o estoque do produto
        update_query = """
            UPDATE produtos SET quantidade_estoque = quantidade_estoque - %s 
            WHERE nome_produto = %s
        """
        cursor.execute(update_query, (quantidade, product_name))

        # Confirmar a transação
        conn.commit()


    except psycopg2.Error as e:
        # Se ocorrer um erro, desfazer a transação e exibir a mensagem de erro
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou inserir no banco de dados: {e}")

    finally:
        # Fechar cursor e conexão
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('compra_realizada.html')




@app.route('/produtos')
def produtos():
    conn = None
    cursor = None
    produtos = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_produto, imagem, quantidade_estoque FROM produtos")
        produtos = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao conectar ou consultar o banco de dados: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('produtos.html', produtos=produtos)

@app.route('/finalizar_pedido', methods=['POST'])
def finalizar_pedido():
    pedido_id = request.form.get('pedido_id')
    
    if not pedido_id:
        flash("ID do pedido não fornecido.")
        return redirect('/admin')
    
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Exclui o pedido da tabela
        delete_query = sql.SQL("DELETE FROM pedidos WHERE id = %s")
        cursor.execute(delete_query, (pedido_id,))
        conn.commit()

        flash(f"Pedido {pedido_id} excluído com sucesso!")
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao excluir o pedido: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect('/admin')

@app.route('/admin')
def admin():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta para obter todos os pedidos agrupados por pedido_grupo
        query = """
            SELECT nome, hora, pedido_grupo, nome_produto, preco, quantidade
            FROM pedidos
            ORDER BY hora DESC
        """
        cursor.execute(query)
        pedidos = cursor.fetchall()

        # Agrupar pedidos pelo pedido_grupo
        pedidos_agrupados = {}
        for pedido in pedidos:
            nome, hora, pedido_grupo, nome_produto, preco, quantidade = pedido
            if pedido_grupo not in pedidos_agrupados:
                pedidos_agrupados[pedido_grupo] = {
                    'nome': nome,
                    'hora': hora,
                    'itens': []
                }
            pedidos_agrupados[pedido_grupo]['itens'].append({
                'nome_produto': nome_produto,
                'preco': preco,
                'quantidade': quantidade
            })

    except psycopg2.Error as e:
        print(f"Erro ao conectar ou consultar o banco de dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('admin.html', pedidos=pedidos_agrupados.values())



@app.route('/login_admin', methods=['POST'])
def login_admin():
    representante = request.form.get('representante')
    senha = request.form.get('senha')

    if not representante or not senha:
        flash("Por favor, preencha todos os campos.")
        return redirect('/login_adm')

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta SQL para verificar se as credenciais são válidas
        query = sql.SQL("SELECT * FROM admin WHERE representante = %s AND senha = %s")
        cursor.execute(query, (representante, senha))

        if cursor.fetchone():
            return redirect("/admin")
        else:
            flash("Usuário ou senha inválidos.")
            return redirect('/login_adm')

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou consultar o banco de dados: {e}")
        flash("Ocorreu um erro no servidor. Tente novamente mais tarde.")
        return redirect('/login_adm')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/login_cliente', methods=['POST'])
def login_cliente_post():
    email = request.form.get('email')
    senha = request.form.get('senha')

    if not email or not senha:
        flash("Por favor, preencha todos os campos.")
        return redirect('/cliente')

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta SQL para verificar se as credenciais são válidas
        query = sql.SQL("SELECT * FROM usuarios WHERE email = %s AND senha = %s")
        cursor.execute(query, (email, senha))

        if cursor.fetchone():
            session['username'] = email  # Armazena o e-mail do usuário na sessão
            return redirect("/compras")
        else:
            flash("Usuário ou senha inválidos. Tente novamente!")
            return redirect('/cliente')

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou consultar o banco de dados: {e}")
        flash("Ocorreu um erro no servidor. Tente novamente mais tarde.")
        return redirect('/cliente')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/cadastro', methods=['POST'])
def cadastro_usuario():
    nome = request.form.get("nome")
    email = request.form.get('email')
    senha = request.form.get('senha')

    if not nome or not email or not senha:
        flash("Por favor, preencha todos os campos.")
        return redirect('/cd')

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta SQL para inserir os dados no banco de dados
        comando = """INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"""
        cursor.execute(comando, (nome, email, senha))
        conn.commit()

        flash("Cadastro realizado com sucesso!")
        return redirect('/cd')

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou inserir no banco de dados: {e}")
        flash("Ocorreu um erro no servidor. Tente novamente mais tarde.")
        return redirect('/cd')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    product_name = request.form.get('nome_produto')
    product_price = request.form.get('preco').replace(',', '.')  # Substitui a vírgula por ponto
    user_email = session.get('username', None)  # Obter e-mail do usuário da sessão

    if not product_name or not product_price or not user_email:
        return redirect('/compras')

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter o nome do usuário a partir do e-mail
        cursor.execute("SELECT nome FROM usuarios WHERE email = %s", (user_email,))
        user_name_row = cursor.fetchone()
        if user_name_row:
            user_name = user_name_row[0]
        else:
            return redirect('/compras')

        # Verificar se o item já está no carrinho
        cursor.execute("SELECT id, quantidade FROM carrinho WHERE nome = %s AND nome_produto = %s", (user_name, product_name))
        existing_item = cursor.fetchone()

        if existing_item:
            # Atualizar a quantidade do item existente
            item_id, quantidade_atual = existing_item
            nova_quantidade = quantidade_atual + 1
            update_query = sql.SQL("""
                UPDATE carrinho
                SET quantidade = %s
                WHERE id = %s
            """)
            cursor.execute(update_query, (nova_quantidade, item_id))
            conn.commit()
        else:
            # Insere um novo item no carrinho
            insert_query = sql.SQL("""
                INSERT INTO carrinho (nome, nome_produto, preco, quantidade)
                VALUES (%s, %s, %s, %s)
            """)
            cursor.execute(insert_query, (user_name, product_name, product_price, 1))
            conn.commit()

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou inserir no banco de dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect('/compras')



@app.route('/remover_do_carrinho', methods=['POST'])
def remover_do_carrinho():
    produto_id = request.form.get('produto_id')

    if not produto_id:
        return redirect('/carrinho')

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Remove o item do carrinho
        delete_query = sql.SQL("DELETE FROM carrinho WHERE id = %s")
        cursor.execute(delete_query, (produto_id,))
        conn.commit()

        return redirect('/carrinho')

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou excluir do banco de dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect('/carrinho')


@app.route('/finalizar_compra', methods=['POST'])
def finalizar_compra():
    user_email = session.get('username', None)

    if not user_email:
        return redirect('/carrinho')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT nome FROM usuarios WHERE email = %s", (user_email,))
        user_name_row = cursor.fetchone()
        if user_name_row:
            usuario_nome = user_name_row[0]
        else:
            return redirect('/carrinho')

        # Obter itens do carrinho
        select_query = sql.SQL("SELECT nome_produto, preco, quantidade FROM carrinho WHERE nome = %s")
        cursor.execute(select_query, (usuario_nome,))
        itens = cursor.fetchall()

        if not itens:
            return redirect('/carrinho')

        pedido_grupo = str(uuid.uuid4())  # Gerar um grupo de pedido único para identificar o pedido
        hora_compra = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for item in itens:
            nome_produto, preco, quantidade = item
            preco_total = Decimal(preco) * Decimal(quantidade)
            
            # Inserir o pedido na tabela pedidos
            insert_query = """INSERT INTO pedidos (nome, nome_produto, preco, quantidade, pedido_grupo, hora) 
                              VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(insert_query, (usuario_nome, nome_produto, preco_total, quantidade, pedido_grupo, hora_compra))

            # Atualizar o estoque do produto
            update_query = """UPDATE produtos SET quantidade_estoque = quantidade_estoque - %s 
                              WHERE nome_produto = %s"""
            cursor.execute(update_query, (quantidade, nome_produto))

        # Remover itens do carrinho
        delete_query = sql.SQL("DELETE FROM carrinho WHERE nome = %s")
        cursor.execute(delete_query, (usuario_nome,))
        conn.commit()

        return redirect('/compras_realizadas')

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao conectar ou inserir no banco de dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect('/carrinho')



@app.route('/carrinho')
def carrinho():
    user_email = session.get('username', None)  # Obter e-mail do usuário da sessão
    conn = None
    cursor = None
    cart_items = []
    total = Decimal('0.00')  # Usar Decimal para o total

    if not user_email:
        return redirect('/cliente')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter o nome do usuário a partir do e-mail
        cursor.execute("SELECT nome FROM usuarios WHERE email = %s", (user_email,))
        user_name_row = cursor.fetchone()
        if user_name_row:
            user_name = user_name_row[0]
        else:
            return redirect('/compras')

        # Consulta SQL para obter itens do carrinho do usuário pelo nome
        query = sql.SQL("SELECT id, nome_produto, preco, quantidade FROM carrinho WHERE nome = %s")
        cursor.execute(query, (user_name,))
        cart_items = cursor.fetchall()

        # Calcular o total dos itens no carrinho
        for item in cart_items:
            produto_id, nome_produto, preco, quantidade = item
            total += Decimal(preco) * Decimal(quantidade)  # Converter preco e quantidade para Decimal

        # Garantir que o total tenha exatamente 2 casas decimais
        total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    except psycopg2.Error as e:
        print(f"Erro ao conectar ou consultar o banco de dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('carrinho.html', cart_items=cart_items, usuario_nome=user_name, total=total)


if __name__ == "__main__":
    app.run(debug=True)
