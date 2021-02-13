# -*- coding: utf-8 -*-

#   CIÊNCIA DA COMPUTAÇÃO
#
#   USO DE METAHEURÍSCA EM UMA FERRAMENTA DE COTAÇÃO PARA COMPRAS DE CARTAS DE MAGIC: THE GATHERING
#   
#   Luiz Eduardo Pereira    

from flask import Flask, jsonify, request, Blueprint, current_app
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient, errors
from unicodedata import normalize
from bson import ObjectId
import json
import os
import sys
from datetime import datetime, timedelta

from db_request import *
from functions import *
from user import User

#######################################################################################################
#                                                                                                     #
#                                                 INIT                                                #
#                                                                                                     #
#######################################################################################################
# CONFIGURAÇÃO
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)
app.config['JWT_SECRET_KEY'] = 'Super_Secret_JWT_KEY'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
CORS(app)
jwt = JWTManager(app)

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
#                                                 ROUTER                                              #
#                                                                                                     #
#######################################################################################################

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - USUARIO JA EXISTE
#   3 - EMAIL JÁ EXISTE
@app.route("/create_user", methods=['POST'])
def create_user():
    try:
        post_data = request.get_json()
        if user_exists(db, post_data.get("username")):
            return jsonify({'status': '2'})
        if email_exists(db, post_data.get("email")):
            return jsonify({'status': '3'})
        else:
            insert_user(db, User(
                post_data.get("username"),
                generate_password_hash(post_data.get("password")),
                post_data.get("name"),
                post_data.get("email"),
                post_data.get("birthdate")
                ))
            return jsonify({'status': '0'})
    except:
        return jsonify({'status': '1'})

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
@app.route('/user/<username>', methods=['GET', 'DELETE'])
@jwt_required
def user(username):
    if request.method == 'GET':
        user = find_user(db, username)
        if (user):
            return jsonify({'status': '0', 'username': user.username, 'name': user.name, 'email': user.email, 'birthdate': user.birthdate, 'entrydate': user.entrydate, 'admin': user.admin})
        else:
            return jsonify({'status': '1'})
    if request.method == 'DELETE':
        if (delete_user(db, username)):
            return jsonify({'status': '0'})
        else:
            return jsonify({'status': '1'})

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - EMAIL JA EXISTE
# ATUALIZA EMAIL DO USUARIO
@app.route('/user/email', methods=['PUT'])
@jwt_required
def user_email():
    try:
        post_data = request.get_json()
        if email_exists(db, post_data.get("email")):
            return jsonify({'status': '2'})
        else:
            if (update_email(db, post_data.get("username"), post_data.get("email")) != None):
                return jsonify({'status': '0'})
            else:
                jsonify({'status': '1'})
    except:
        return jsonify({'status': '1'})

#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - SENHA INCORRETA
# ATUALIZA SENHA DO USUARIO
@app.route('/user/password', methods=['PUT'])
@jwt_required
def user_password():
    try:
	    post_data = request.get_json()
	    user = find_user(db, post_data.get("username"))
	    if (user.check_password(post_data.get("password"))):
	        new_password = generate_password_hash(post_data.get("newPassword"))
	        if (update_password(db, user.username, new_password) != None):
	            return jsonify({'status': '0'})
	        else:
	            jsonify({'status': '1'})
	    else:
	        return jsonify({'status': '2'})
    except:
        return jsonify({'status': '1'})

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - POSSUI CARTAS NÃO RECONHECIDAS
#   3 - SINTAXE INCORRETA
# CRIAÇÃO DE REQUISIÇÃO DE COTAÇÃO DE PREÇO
@app.route("/request_list", methods=['POST'])
@jwt_required
def request_list():
    post_data = request.get_json()
    if (len(post_data.get("card_list")) == 0):
        return(jsonify({'status': '3'}))
    try:
        error_list = register_request(db, post_data.get("deck_name"), post_data.get("card_list"), post_data.get("username"))
        if (error_list == None):
            return jsonify({'status': '3'})
        elif (error_list == []):
            return jsonify({'status': '0'})
        else:
            return jsonify({'status': '2', 'error_list': error_list})
    except:
        return jsonify({'status': '1'})

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - ACESSO NEGADO
# INSERÇÃO DE CARTAS NO BANCO DE NOMES DE CARTAS
@app.route("/insert_card_names", methods=['POST'])
@jwt_required
def insert_card_names():
    try:
        storage_cards(db, request.files['file'].read())
        return jsonify({'status': '0'})
    except:
        return jsonify({'status': '1'})

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
# RETORNA HISTORICO DE COTAÇÕES DO USUARIO
@app.route("/history/<username>", methods=['GET'])
@jwt_required
def history(username):
    try:
        result = find_result(db, username)
        return jsonify({'status': '0', 'history': result})
    except:
        return jsonify({'status': '1'})

#######################################################################################################
#                                                                                                     #
#                                           ROUTER - LOGIN                                            #
#                                                                                                     #
#######################################################################################################

# STATUS:
#   0 - SUCESSO
#   1 - OCORREU UM PROBLEMA INESPERADO
#   2 - USUARIO OU SENHA INCORRETOS
@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.json['username']
        password = request.json['password']
        user = find_user(db, username)  # BUSCA USUARIO
        if (user):
            if (user.check_password(password)):  # CHECA SE SENHA ESTA CORRETA
                access_token = create_access_token(identity=username)
                return jsonify({'status': 0, 'token': access_token})
            else:
                return jsonify({'status': 2})
        else:
            return jsonify({'status': 2})
    except:
        return jsonify({'status': 1})

@app.route('/verify-token', methods=['POST'])
@jwt_required
def verify_token():
    return jsonify({'success': True}), 200

@app.route('/protected', methods=['GET'])
@jwt_required
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

#######################################################################################################
#                                                                                                     #
#                                               INIT                                                  #
#                                                                                                     #
#######################################################################################################

if __name__ == "__main__":
    app.run()
