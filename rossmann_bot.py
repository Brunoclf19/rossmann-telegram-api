import os
import pandas as pd
import json
import requests
import logging

from flask import Flask, request, Response

# TOKEN = 8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA
# getMe - info about bot 
# https://api.telegram.org/bot8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA/getMe 

# get updates 
# https://api.telegram.org/bot8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA/getUpdates 

# Webhook
# https://api.telegram.org/bot8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA/setWebhook?url=

# send message 
# https://api.telegram.org/bot8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA/sendMessage?chat_id=1907985452&text=Hi Bruno, I'm doing good, thanks!

# ---- CONFIG ----
TOKEN = '8212313991:AAElRsQ6GdEkYD2ADAppnVIQMUuf1w4TiJA'
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'
PREDICT_URL = 'https://teste-api-render-bzme.onrender.com/rossmann/predict'

# logging básico
logging.basicConfig(level=logging.INFO)

def send_message(chat_id, text):
    try:
        r = requests.post(
            f'{TELEGRAM_API}/sendMessage',
            json={'chat_id': chat_id, 'text': text},
            timeout=15
        )
        logging.info('send_message status=%s body=%s', r.status_code, r.text)
    except Exception as e:
        logging.exception('Erro em send_message: %s', e)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')

def load_dataset(store_id):
    # Ajuste os caminhos se necessário
    test_path  = os.path.join(DATA_DIR, 'test.csv')
    store_path = os.path.join(DATA_DIR, 'store.csv')

    df10 = pd.read_csv(test_path)
    df_store_raw = pd.read_csv(store_path)

    df_test = pd.merge(df10, df_store_raw, how='left', on='Store')
    df_test = df_test[df_test['Store'] == store_id]

    if df_test.empty:
        return 'error'

    # remove dias fechados
    df_test = df_test[df_test['Open'] != 0]
    df_test = df_test[~df_test['Open'].isnull()]
    if 'Id' in df_test.columns:
        df_test = df_test.drop('Id', axis=1)

    # se depois de filtrar ficar vazio:
    if df_test.empty:
        return 'error'

    # para JSON
    data = df_test.to_dict(orient='records')
    return json.dumps(data)

def predict(data):
    try:
        r = requests.post(
            PREDICT_URL,
            data=data,
            headers={'Content-type': 'application/json'},
            timeout=30
        )
        logging.info('predict status=%s', r.status_code)
        r.raise_for_status()
        js = r.json()
        if not js:
            raise ValueError('Resposta vazia da API de previsão.')
        d1 = pd.DataFrame(js, columns=js[0].keys())
        return d1
    except Exception as e:
        logging.exception('Erro na previsão: %s', e)
        return None

def parse_message(message):
    """
    Aceita message ou edited_message; retorna (chat_id, store_id|error)
    """
    obj = message.get('message') or message.get('edited_message') or {}
    chat = obj.get('chat') or {}
    text = obj.get('text', '')

    chat_id = chat.get('id')
    if not chat_id:
        return None, 'error'

    store_id = text.replace('/', '').strip()
    try:
        store_id = int(store_id)
    except:
        store_id = 'error'

    return chat_id, store_id

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return 'ok', 200

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return '<h1> Rossmann Telegram BOT </h1>'

    # POST do Telegram (webhook)
    try:
        message = request.get_json(force=True, silent=True) or {}
        logging.info('Update recebido: %s', message)

        chat_id, store_id = parse_message(message)

        if chat_id is None:
            # estrutura inesperada
            return Response('No chat_id', status=200)

        if store_id == 'error':
            send_message(chat_id, 'Por favor, envie apenas o número da loja. Ex.: 1001')
            return Response('Ok', status=200)

        data = load_dataset(store_id)
        if data == 'error':
            send_message(chat_id, f'Loja {store_id} não encontrada ou sem dias abertos.')
            return Response('Ok', status=200)

        d1 = predict(data)
        if d1 is None or d1.empty:
            send_message(chat_id, 'Não consegui obter a previsão no momento. Tente novamente mais tarde.')
            return Response('Ok', status=200)

        d2 = d1[['Store', 'predictions']].groupby('Store', as_index=False).sum()

        # Formatação simples en-US (R$ 1,234,567.89). Se quiser pt-BR, dá pra trocar depois.
        store = int(d2['Store'].iloc[0])
        total = float(d2['predictions'].iloc[0])

        msg = f'A loja {store}: venderá R${total:,.2f} nas próximas 6 semanas.'
        send_message(chat_id, msg)
        return Response('Ok', status=200)

    except Exception as e:
        logging.exception('Erro no handler: %s', e)
        return Response('Ok', status=200)

if __name__ == '__main__':
    # Em produção, use gunicorn/uwsgi. Local: tudo bem.
    port = os.environ.get('PORT', 5000)
    app.run(host='0.0.0.0', port=port)
