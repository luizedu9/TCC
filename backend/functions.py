# -*- coding: utf-8 -*-

#	CIÊNCIA DA COMPUTAÇÃO
#
#	USO DE METAHEURÍSCA EM UMA FERRAMENTA DE COTAÇÃO PARA COMPRAS DE CARTAS DE MAGIC: THE GATHERING
#	
#	Luiz Eduardo Pereira	

import json
from unicodedata import normalize

from db_request import *

#######################################################################################################
#                                                                                                     #
#                                               PRIVATE                                               #
#                                                                                                     #
#######################################################################################################

# REFERENCIA: https://wiki.python.org.br/RemovedorDeAcentos
def accent_removal(string):
	return normalize('NFKD', string).encode('ASCII', 'ignore').decode('ASCII')

def accent_removal_list(cards):
    new_cards = []
    for card in cards:
        if (str(card).strip()):  # SE VAZIO, IGNORA
            new_cards.append(normalize('NFKD', card).encode(
            	'ASCII', 'ignore').decode('ASCII').lower().strip())
    return new_cards

# TRANSFORMA card_list EM card_dict
def request_to_dict(card_list):
    card_dict = {}
    try:
        cards = card_list.splitlines()
        cards = accent_removal_list(cards)
        for card in cards:
            if (str(card).strip()):  # SE VAZIO, IGNORA
                card_dict[card.split(" ", 1)[1]] = card.split(" ", 1)[0]
    except:
        card_dict = None
    return(card_dict)

# VERIFICA SE ALGUMA CARTA NÃO SE ENCONTRA NO BANCO DE DADOS
def names_resolver(db, card_dict):
    if (card_dict == None):
        return (None)
    error_list = []
    for key, value in card_dict.items():
        if (not(value.isdigit())):  # VERIFICA SE FOI PASSADO A QUANTIDADE DA CARTA
            error_list.append(str(value) + ' ' + str(key) + ' (Quantidade requerida)')
        else:  # VERIFICA SE A CARTA PASSADA NÃO SE ENCONTRA NO BANCO DE DADOS EM INGLES OU PORTUGUES
            try:
                english = find_name_english(db, key)
                portuguese = find_name_portuguese(db, key)
            except:
                raise Exception('find_name_...()')
            if (not(english) and not(portuguese)):
                error_list.append(str(value) + ' ' + str(key) + ' (Carta inexistente)')
    return(error_list)

#######################################################################################################
#                                                                                                     #
#                                                PUBLIC                                               #
#                                                                                                     #
#######################################################################################################

def register_request(db, deck_name, card_list, user_logged):
	card_dict = request_to_dict(card_list) # TRANSFORMA LISTA DE CARTAS EM DICIONARIO
	error_list = names_resolver(db, card_dict) # VERIFICA SE CARTAS EXISTEM NO BANCO DE DADOS
	if ((error_list != None) and (len(error_list) == 0)): # SE NÃO ENCONTROU ERRO, SALVA REQUISIÇÃO NO BANCO DE DADOS
		increment_length_queue(db) # ATUALIZA TAMANHO DA FILA
		insert_request(db, get_length_queue(db), user_logged, card_dict, deck_name)
	return(error_list)

# ADICIONA OS NOMES DAS CARTAS NO BANCO. RECEBE UM file.read() COMO mtg_cards
def storage_cards(db, mtg_cards):
	dictionary = json.loads(mtg_cards)
	# PEGA CADA NOME DE CARTA EM INGLES E PORTUGUES E ARMAZENA NO BANCO
	for key in dictionary['data']:
		# REMOVE OS CARACTERES ESPECIAIS E DEIXA LETRAS MINUSCULAS
		card_english = accent_removal(key).lower()
		card_portuguese = ''
		try:
			insert_card(db, card_english, card_portuguese)
		except:
			raise Exception('ERROR: Can\'t insert card into db')
