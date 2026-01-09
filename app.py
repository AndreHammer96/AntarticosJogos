from flask import Flask, render_template, send_from_directory
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import os
import traceback

app = Flask(__name__)

GOOGLE_SHEET_ID = "1r6cN3EUgMj-6SzbW4HLUg5KTvtJDPBN-4_B7YUgUWDQ"
GID_JOGOS = "1122642369"
GOOGLE_SHEETS_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export"
    f"?format=csv&gid={GID_JOGOS}"
)

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


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "img"),
        "logo_v2.png",
        mimetype="image/png"
    )


if __name__ == "__main__":
    app.run(debug=True)
