from flask import request, jsonify
from flask import Flask, render_template, send_from_directory
import json
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import os
import traceback
import gspread
from google.oauth2.service_account import Credentials


app = Flask(__name__)

GOOGLE_SHEET_ID = "1r6cN3EUgMj-6SzbW4HLUg5KTvtJDPBN-4_B7YUgUWDQ"
GID_JOGOS = "1122642369"
GOOGLE_SHEETS_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export"
    f"?format=csv&gid={GID_JOGOS}"
)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "@Antarticos2026.#")

def normalizar_valor(valor):
    if pd.isna(valor):
        return {"jogou": False, "flag": None}

    if isinstance(valor, (int, float)):
        if valor == 1:
            return {"jogou": True, "flag": None}
        return {"jogou": False, "flag": None}

    v = str(valor).strip().upper()

    if v == "1":
        return {"jogou": True, "flag": None}
    if v == "F":
        return {"jogou": True, "flag": "F"}
    if v == "T":
        return {"jogou": True, "flag": "T"}

    return {"jogou": False, "flag": None}


def carregar_dados_planilha():
    r = requests.get(GOOGLE_SHEETS_URL)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.upper()
    return df


@app.route("/")
def index():
    try:
        df = carregar_dados_planilha()
    except Exception:
        traceback.print_exc()
        return "<h3>Erro ao carregar planilha</h3>"

    col_datas = [c for c in df.columns if c not in ["JOGADOR", "JOGOS TOTAL"]]

    nomes = df["JOGADOR"].tolist()
    separador_index = None
    vazios = 0
    for i, nome in enumerate(nomes):
        if pd.isna(nome) or str(nome).strip() == "":
            vazios += 1
            if vazios >= 4:
                separador_index = i
                break
        else:
            vazios = 0

    jogadores = []

    for i, row in df.iterrows():
        nome = row["JOGADOR"]
        if pd.isna(nome) or str(nome).strip() == "":
            continue

        tipo = "convidado" if separador_index and i > separador_index else "time"

        jogos = {}
        total_jogos = 0
        total_f = 0
        total_t = 0

        for col in col_datas:
            info = normalizar_valor(row[col])
            jogos[col] = info
            if info["jogou"]:
                total_jogos += 1
                if info["flag"] == "F":
                    total_f += 1
                if info["flag"] == "T":
                    total_t += 1

        jogadores.append({
            "nome": str(nome).strip(),
            "tipo": tipo,
            "jogos": jogos,
            "total_jogos": total_jogos,
            "trofeu_f": total_f,
            "trofeu_t": total_t
        })

    atualizado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return render_template(
        "index.html",
        jogadores=jogadores,
        col_datas=col_datas,
        atualizado_em=atualizado_em
    )
def conectar_planilha():
    private_key = os.environ.get("GOOGLE_PRIVATE_KEY")
    client_email = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")

    if not private_key or not client_email:
        raise RuntimeError("Credenciais Google não configuradas corretamente")

    creds_dict = {
        "type": "service_account",
        "client_email": client_email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token"
    }

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(GID_JOGOS))


@app.route("/api/jogo", methods=["GET"])
def carregar_jogo():
    feijoada = None
    thy = None

    data_iso = request.args.get("data")
    data_jogo = formatar_data_planilha(data_iso)

    if not data_jogo:
        return jsonify({"jogadores": []})

    ws = conectar_planilha()
    dados = ws.get_all_values()

    headers = dados[0]

    if data_jogo not in headers:
        return jsonify({"jogadores": []})

    col_index = headers.index(data_jogo)

    jogadores = []

    for i in range(1, len(dados)):
        linha = dados[i]

        if not linha or len(linha) <= col_index:
            continue

        nome = linha[0].strip()
        valor = str(linha[col_index]).strip().upper()

        if valor == "1":
            jogadores.append(nome)
        elif valor == "F":
            jogadores.append(nome)
            feijoada = nome
        elif valor == "T":
            jogadores.append(nome)
            thy = nome

    return jsonify({
        "jogadores": jogadores,
        "feijoada": feijoada,
        "thy": thy
    })




@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "img"),
        "logo_v2.png",
        mimetype="image/png"
    )
@app.route("/api/jogo", methods=["POST"])
def salvar_jogo():
    try:
        data = request.json
        feijoada = data.get("feijoada")
        thy = data.get("thy")

        senha = data.get("senha", "").strip()
        data_iso = data.get("data")
        jogadores = data.get("jogadores", [])

        if senha != ADMIN_PASSWORD:
            return jsonify({"erro": "senha"}), 403

        if not data_iso:
            return jsonify({"erro": "data"}), 400

        # 🔥 CONVERSÃO ÚNICA E OBRIGATÓRIA
        data_jogo = formatar_data_planilha(data_iso)

        ws = conectar_planilha()
        dados = ws.get_all_values()

        headers = dados[0]

        # 🔒 SE JÁ EXISTE, USA — SE NÃO, CRIA
        if data_jogo in headers:
            col_index = headers.index(data_jogo)
        else:
            ws.add_cols(1)
            col_index = len(headers)
            ws.update_cell(1, col_index + 1, data_jogo)

        jogadores_upper = {j.upper() for j in jogadores}

        updates = []

        for i in range(1, len(dados)):
            linha = dados[i]
            if not linha or not linha[0]:
                continue

            nome = linha[0].strip().upper()
            if feijoada and nome == feijoada.upper():
                valor = "F"
            elif thy and nome == thy.upper():
                valor = "T"
            elif nome in jogadores_upper:
                valor = "1"
            else:
                valor = "0"



            updates.append({
                "range": gspread.utils.rowcol_to_a1(i + 1, col_index + 1),
                "values": [[valor]]
            })

        if updates:
            ws.batch_update(updates)

        return jsonify({"ok": True})

    except Exception as e:
        print("ERRO AO SALVAR:", e)
        traceback.print_exc()
        return jsonify({"erro": "interno"}), 500



def formatar_data_planilha(data_iso):
    # YYYY-MM-DD -> DD/MM/YYYY
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return None

if __name__ == "__main__":
    app.run(debug=True)

