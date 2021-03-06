# -*- coding: utf-8 -*-

#   CIÊNCIA DA COMPUTAÇÃO
#
#   USO DE METAHEURÍSCA EM UMA FERRAMENTA DE COTAÇÃO PARA COMPRAS DE CARTAS DE MAGIC: THE GATHERING
#   
#   Luiz Eduardo Pereira    

from pymongo import MongoClient
import smtplib
from contextlib import contextmanager
import os
import sys
import logging
import time

from db_request import *

#######################################################################################################
#                                                                                                     #
#                                                 INIT                                                #
#                                                                                                     #
#######################################################################################################

client = MongoClient('localhost', 27017)
db = client["scryx"]
try:
    client.server_info()
except:
    log.error('Can\'t connect to MongoDB')
    exit()

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
log.addHandler(handler)

# CONFIGURAÇÕES DO E-MAIL 
email_from = "scryx.magic@gmail.com"
password = "scryxscryx"

# REFERENCIA: https://stackoverflow.com/questions/431684/how-do-i-change-directory-cd-in-python
@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)

# CHAMA O CRAWLER E O SIMULATED ANNEALING
def research_assistant(request_id):
    log.info('Crawler iniciado')
    with cd('../crawler'):
        os.system('python3 -B run_crawler.py ' + request_id)
    log.info('Simulated Annealing iniciado')
    with cd('../simulated_annealing'):
        os.system('python3 -B run_simulated_annealing.py ' + request_id)

# ENVIA EMAIL PARA USUARIO NOTIFICANDO QUE A COTAÇÃO TERMINOU
def send_email(request_id):
    result = find_result_id(db, request_id)
    email_to = find_user_email(db, result['user'])
    subject = str("ScryX - " + result['deck_name'])
    body = str('Informamos que a lista ' + str(result['deck_name']) + ' terminou de cotar com sucesso. \nEntre agora no nosso site para ver o resultado.\n\nAtt. \nEquipe ScryX')
    message = "Subject:{}\n\n{}".format(subject, body)
    try:
        smOb = smtplib.SMTP('smtp.gmail.com', 587)  # Opening the Connection
        smOb.starttls()  # Using a Secure Connection (TLS)
        smOb.login(email_from, password)  # Login to the Gmail
        smOb.sendmail(email_from, email_to, message)  # Send Email
        smOb.quit()  # Logout from the email
    except Exception as e:
        print(e)

# SE EXISTIR REQUISIÇÕES, EXECUTA, CASO CONTRARIO, ESPERA
while (True):
    if (int(get_length_queue(db)) > int(get_current_queue(db))): # SE EXISTE REQUISIÇÕES NA LISTA DE ESPERA, ATENDA
        try:
            current_id = str(int(get_current_queue(db)) + 1)
            log.info('------------------------------------------------------------')
            log.info('Requisição ' + str(current_id) + ' iniciada')
            research_assistant(current_id)
            send_email(current_id)
            increment_current_queue(db) # CONFIRMA QUE TERMINOU COM SUCESSO A EXECUÇÃO
            log.info('Requisição ' + str(current_id) + ' finalizada com sucesso')
            log.info('------------------------------------------------------------')
        except:
            log.error('Requisição ' + str(current_id) + ' interrompida com erro')
    else: # ESPERA UM TEMPO ANTES DE FAZER UMA NOVA VERIFICAÇÃO
        log.info('Esperando...')
        time.sleep(10)
