from flask import Flask, render_template
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import json
import traceback
from flask import send_from_directory
import os



app = Flask(__name__)

# ===== CONFIGURAÇÕES =====
GOOGLE_SHEET_ID = "1r6cN3EUgMj-6SzbW4HLUg5KTvtJDPBN-4_B7YUgUWDQ"
GID_JOGOS = "1122642369" 
GOOGLE_SHEETS_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid={GID_JOGOS}"
# ==========================


def carregar_dados_planilha():
    """Baixa a aba JOGOS do Google Sheets e converte em DataFrame."""
    try:
        response = requests.get(GOOGLE_SHEETS_URL)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), encoding='utf-8-sig')

        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        print("❌ Erro ao carregar planilha:", e)
        traceback.print_exc()
        return None


@app.route('/')
def index():
    df = carregar_dados_planilha()
    if df is None:
        return "<h3>Erro ao carregar a planilha. Verifique o link e o GID da aba 'JOGOS'.</h3>"

    if 'JOGADOR' not in df.columns or 'JOGOS TOTAL' not in df.columns:
        return "<h3>Planilha inválida: precisa ter colunas 'JOGADOR' e 'JOGOS TOTAL'.</h3>"

    # --- Identifica as colunas de datas ---
    col_datas = [c for c in df.columns if c not in ['JOGADOR', 'JOGOS TOTAL']]

    # --- Detecta separação entre time e convidados (4 linhas vazias) ---
    nomes = df['JOGADOR'].tolist()
    blocos_vazios = 0
    separador_index = None
    for i, nome in enumerate(nomes):
        if pd.isna(nome) or str(nome).strip() == "":
            blocos_vazios += 1
            if blocos_vazios >= 4:
                separador_index = i
                break
        else:
            blocos_vazios = 0

    # --- Constrói lista de jogadores ---
    jogadores = []
    for i, row in df.iterrows():
        nome = row['JOGADOR']
        if pd.isna(nome) or str(nome).strip() == "":
            continue
        tipo = "convidado" if separador_index and i > separador_index else "time"
        jogos = {col: int(row[col]) if pd.notna(row[col]) else 0 for col in col_datas}
        total = int(row['JOGOS TOTAL']) if not pd.isna(row['JOGOS TOTAL']) else sum(jogos.values())
        jogadores.append({
            "nome": str(nome).strip(),
            "total": total,
            "jogos": jogos,
            "tipo": tipo
        })

    atualizado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return render_template(
    'index3.html',
    jogadores=jogadores,
    col_datas=col_datas,
    atualizado_em=atualizado_em
)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'img'),
        'logo_v2.png', mimetype='image/png'
    )

@app.route('/debug')
def debug_json():
    df = carregar_dados_planilha()
    if df is None:
        return {"erro": "não conseguiu carregar planilha"}

    col_datas = [c for c in df.columns if c not in ['JOGADOR', 'JOGOS TOTAL']]
    jogadores = []
    for _, row in df.iterrows():
        jogador = {
            'nome': str(row['JOGADOR']).strip(),
            'total': int(row['JOGOS TOTAL']) if not pd.isna(row['JOGOS TOTAL']) else 0,
            'jogos': {data: int(row[data]) if not pd.isna(row[data]) else 0 for data in col_datas}
        }
        jogadores.append(jogador)

    return {"jogadores": jogadores, "datas": col_datas}



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
