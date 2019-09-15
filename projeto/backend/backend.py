# -*- coding: utf-8 -*-

#   CIÊNCIA DA COMPUTAÇÃO
#
#   USO DE METAHEURÍSCA EM UMA FERRAMENTA DE COTAÇÃO PARA COMPRAS DE CARTAS DE MAGIC: THE GATHERING
#   
#   Luiz Eduardo Pereira    

from flask import Flask, jsonify, request, Blueprint, current_app
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from pymongo import MongoClient, errors
import logging as log
from unicodedata import normalize
from bson import ObjectId
import os
import sys
import jwt
from datetime import datetime, timedelta
from functools import wraps

from db_request import *
from functions import *
from user import User

BOOKS = [
    {}
]

#######################################################################################################
#                                                                                                     #
#                                                 INIT                                                #
#                                                                                                     #
#######################################################################################################
# CONFIGURAÇÃO
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

# ENABLE CORS
CORS(app, resources={r'/*': {'origins': '*'}})

# CONECTA COM MONGODB
client = MongoClient('localhost', 27017)
try:
    # INICIA BD, SE NÃO EXISTIR, CRIA UM
    if ('scryx' not in client.list_database_names()):
        db = client["scryx"]
        insert_current_queue(db)
        insert_length_queue(db)
    else:
        db = client["scryx"]        
    client.server_info()
except:
    log.error('Can\'t connect to MongoDB')
    exit()

try: # CARREGA GERENCIADOR DE FILA
    current_queue = get_current_queue(db)
    length_queue = get_length_queue(db)
except:
    log.error('Can\'t read current_queue or length_queue')
    exit()

#######################################################################################################
#                                                                                                     #
#                                                 TOKEN                                               #
#                                                                                                     #
#######################################################################################################

# https://stackabuse.com/single-page-apps-with-vue-js-and-flask-jwt-authentication/
def token_required(f):
    @wraps(f)
    def _verify(*args, **kwargs):
        auth_headers = request.headers.get('Authorization', '').split()
        invalid_msg = {'message': 'Token invalido.', 'authenticated': False}
        expired_msg = {'message': 'Token expirado', 'authenticated': False}
        if len(auth_headers) != 2:
            return jsonify(invalid_msg), 401
        try:
            token = auth_headers[1]
            data = jwt.decode(token, str(current_app.config['SECRET_KEY']))
            user = find_user(db, data['sub'])
            if not user:
                raise RuntimeError('User not found')
            return f(user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            # 401 is Unauthorized HTTP status code
            return jsonify(expired_msg), 401
        except (jwt.InvalidTokenError, Exception) as e:
            print(e)
            return jsonify(invalid_msg), 401
    return _verify

#######################################################################################################
#                                                                                                     #
#                                                 ROUTER                                              #
#                                                                                                     #
#######################################################################################################

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - USUARIO JA EXISTE
@app.route("/create_user", methods=['POST'])
def create_user():
    try:
        post_data = request.get_json()
        if user_exists(db, post_data.get("username")): # SE USUARIO JA EXISTE, NÃO CONTINUA
            return jsonify({'status': '2'})
        else:
            insert_user(db, User(
                post_data.get("username"),
                generate_password_hash(post_data.get("password")),
                post_data.get("name"),
                post_data.get("email"),
                post_data.get("birthdate"),
                post_data.get("gender")
                ))
            response_object = {'status': '0'}
    except:
        response_object = {'status': '1'}
    return jsonify(response_object)

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - USUARIO OU SENHA INCORRETOS
@app.route("/login", methods=['POST'])
def login():
    #try:
    post_data = request.get_json()
    user = find_user(db, post_data.get("username")) # BUSCA USUARIO
    if (user != False):
        if (user.check_password(post_data.get("password"))): # CHECA SE SENHA ESTA CORRETA            
            token = jwt.encode({'sub': user.username, 'iat': datetime.utcnow(), 'exp': datetime.utcnow() + timedelta(minutes=30)}, str(current_app.config['SECRET_KEY']))
            print(str(token), file=sys.stderr)
            return jsonify({'token': token.decode('UTF-8')})
        else:
            return jsonify({'message': 'Usuário ou senha incorretos', 'authenticated': False})
    else:
        return jsonify({'message': 'Usuário ou senha incorretos', 'authenticated': False})
    #except:
    #    return jsonify({'message': 'Houve um problema inesperado', 'authenticated': False})

# CRIAÇÃO DE REQUISIÇÃO DE COTAÇÃO DE PREÇO
# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
@app.route("/request_list", methods=['POST'])
@token_required
def request_list():
    post_data = request.get_json()
    try:
        error_list = register_request(db, post_data.get("card_list"), user_logged)
        if (error_list == []):
            response_object = {'status': '0'}
        else:
            response_object = {'error_list': error_list}
    except:
        response_object = {'status': '1'}
    return jsonify(response_object)

# INSERÇÃO DE CARTAS NO BANCO DE NOMES DE CARTAS
# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
@app.route("/insert_card_names", methods=['POST'])
def insert_card_names():
    print('This is error output', file=sys.stderr)
    try:
        storage_cards(db, request.files['file'].read())
        response_object = {'status': '0'}   
    except:
        response_object = {'status': '1'}
    return jsonify(response_object)
    
#######################################################################################################
#                                                                                                     #
#                                                  EXEMPLO                                            #
#                                                                                                     #
#######################################################################################################

def remove_book(book_id):
    for book in BOOKS:
        if book['id'] == book_id:
            BOOKS.remove(book)
            return True
    return False

# sanity check route
@app.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify('pong!')

@app.route('/books', methods=['GET', 'POST'])
def all_books():
    response_object = {'status': 'success'}
    if request.method == 'POST':
        post_data = request.get_json()
        BOOKS.append({
            'id': uuid.uuid4().hex,
            'title': post_data.get('title'),
            'author': post_data.get('author'),
            'read': post_data.get('read')
        })
        response_object['message'] = 'Book added!'
    else:
        response_object['books'] = BOOKS
    return jsonify(response_object)


@app.route('/books/<book_id>', methods=['PUT', 'DELETE'])
def single_book(book_id):
    response_object = {'status': 'success'}
    if request.method == 'PUT':
        post_data = request.get_json()
        remove_book(book_id)
        BOOKS.append({
            'id': uuid.uuid4().hex,
            'title': post_data.get('title'),
            'author': post_data.get('author'),
            'read': post_data.get('read')
        })
        response_object['message'] = 'Book updated!'
    if request.method == 'DELETE':
        remove_book(book_id)
        response_object['message'] = 'Book removed!'
    return jsonify(response_object)

if __name__ == "__main__":
    app.run()

#print('This is error output', file=sys.stderr)
