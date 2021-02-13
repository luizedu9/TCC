# -*- coding: utf-8 -*-

#   CIÊNCIA DA COMPUTAÇÃO
#
#   USO DE METAHEURÍSCA EM UMA FERRAMENTA DE COTAÇÃO PARA COMPRAS DE CARTAS DE MAGIC: THE GATHERING
#   
#   Luiz Eduardo Pereira    
#
#   frantic_search.py:
#   Este modulo extrai os dados necessarios das cartas 
#   É utilizado o site ligamagic como raiz para o scrapy

import scrapy
from pymongo import MongoClient
import logging as log

# GERA O LINK DA CARTA
def card_link_mount(card):
    return ('https://www.ligamagic.com.br/?view=cards/card&card=' + card.replace(' ', '+'))

# GERA O LINK DA LOJA    
def store_link_mount(store):
    return ('https://www.ligamagic.com.br/' + store)

class CrawlerSpider(scrapy.Spider):
    name = 'crawler'
    start_urls = ['https://www.ligamagic.com.br/']

    # REFERENTE A CARTA
    def parse(self, response):
        
        client = MongoClient('localhost',27017)
        db = client["scryx"]
        try:
            client.server_info()
        except:
            log.error('Can\'t connect to MongoDB')
            exit()

        card_dict = db.request.find_one({'_id': self.id})
        
        for card in card_dict['cards']:
            yield scrapy.Request(url=card_link_mount(card), callback=self.parse_page, meta={'card': card})
        
    # REFERENTE A LOJA
    def parse_page(self, response):

        store_name_xpath = response.xpath('//div[@class="e-col1"]/img')
        names = store_name_xpath.xpath('./@title').extract()
        store_link_xpath = response.xpath('//div[@class="e-col7"]/div[3]/a')
        links = store_link_xpath.xpath('./@href').extract()        

        for link, name in zip(links, names):
            yield scrapy.Request(url=store_link_mount(link), callback=self.parse_item, meta={'card_store': (response.meta['card'], name)})

    # REFERENTE AOS VALORES DA CARTA EM DETERMINADA LOJA
    def parse_item(self, response):
        card, store = response.meta['card_store']

        # EXISTEM DOIS PADRÕES DE HTML, UM COM O MENU "EXTRA" E OUTRO SEM. ISSO INFLUENCIA EM QUAL INDEX DO 'TD' DEVE SER ESCOLHIDO PARA ENCONTRAR OS valueES
        option = response.xpath('//td[@class="tdHeader"]/text()').extract()
        op = 0
        if ("Extras" in option):
            op = 1

        tr = response.xpath('//*[starts-with(@onmouseover, "itemMouseOver")]')
        quantity = tr.xpath('./td[' + str(4 + op) + ']/text()').extract() # SE EXISTE O NO MENU A OPÇÃO "EXTRA", ENTÃO A QUANTIDADE DE CARTAS ESTARÁ LOCALIZADA NO TD[5]
        value = tr.xpath('./td[' + str(5 + op) + ']')

        for i in range(0, len(value)):
            if ('0 unid.' in quantity[i]): # NÃO EXISTE ESTOQUE DESTA CARTA
                pass
            elif ("desconto" in value[i].extract()): # POSSUI DESCONTO, MODO DE SCRAPYING DIFERENTE
                price = (''.join(value[i].xpath('./font/text()').extract())).split()[1].replace('.', '').replace(',', '.')
                if (price != '0.00'):
                    yield {'id': self.id, 'card': card, 'store': store, 'quantity': quantity[i].split()[0], 'value': price}
            else:
                price = (''.join(value[i].xpath('./text()').extract())).split()[1].replace('.', '').replace(',', '.')
                if (price != '0.00'):
                    yield {'id': self.id, 'card': card, 'store': store, 'quantity': quantity[i].split()[0], 'value': price}
