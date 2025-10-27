import os
from flask import Flask, render_template, request
from google import genai
from google.genai import types

app = Flask(__name__)

# *****************************************************************
# ATENÇÃO: COLOQUE SUA CHAVE DE API REAL AQUI!
# AVISO: A chave está exposta no código-fonte, evite fazer isso
# em produção ou em repositórios públicos.
# *****************************************************************
GEMINI_API_KEY = "AIzaSyAiYnR5NgtCxbBO4GsWKTofzKClLXP2jBU"


# --- FUNÇÃO DE BUSCA DA PEÇA (OTIMIZADA) ---
def buscar_codigo_peca(nome_peca: str):
    """
    Busca o código de uma peça automotiva e retorna um dicionário com os resultados.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "SUA CHAVE DE API REAL AQUI":
        # Retorna um erro genérico se a chave ainda for o placeholder
        return {
            "resultado": "ERRO: Insira sua chave de API real no arquivo app.py.",
            "tokens": {"total": 0},
            "fontes": [],
            "status": "error"
        }

    try:
        # 1. Inicializa o cliente Gemini
        client = genai.Client(api_key=GEMINI_API_KEY)

        # 2. PROMPT OTIMIZADO (para economia de tokens)
        prompt = (
            f"Busque e retorne os códigos de referência cruzada de fabricantes"
            f"Busque os códigos de referência cruzada de fabricantes para o item: {nome_peca}. Responda apenas com 'MARCA - PEÇA (OPCIONAL) = CÓDIGO'. Se for um kit, liste os subitens separadamente."
        )

        # 3. CONFIGURAÇÃO DE GERAÇÃO
        config = types.GenerateContentConfig(
            # Limita os tokens de saída para economizar
            max_output_tokens=250,
            tools=[
                types.Tool(
                    # Ativa o Grounding com Pesquisa Google
                    google_search=types.GoogleSearch()
                )
            ]
        )

        # 4. Chama a API
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',  # Modelo mais econômico
            contents=prompt,
            config=config,
        )

        # Inicializa as variáveis de resultado
        resultado_texto = response.text
        tokens_uso = {"prompt": 0, "candidato": 0, "total": 0}
        fontes_lista = []
        # 5. Captura o uso de tokens
        if response.usage_metadata:
            usage = response.usage_metadata
            tokens_uso = {
                "prompt": usage.prompt_token_count,
                "candidato": usage.candidates_token_count,
                "total": usage.total_token_count
            }

        # 6. Captura as Citações (limitado a 2 para velocidade)
        if response.candidates and response.candidates[0].grounding_metadata:
            grounding = response.candidates[0].grounding_metadata

            for i, chunk in enumerate(grounding.grounding_chunks):
                if i >= 2:  # Limita a APENAS 2 links
                    break
                if chunk.web:
                    fontes_lista.append({
                        "titulo": chunk.web.title,
                        "uri": chunk.web.uri
                    })

        # Retorna o resultado com sucesso
        return {
            "resultado": resultado_texto,
            "tokens": tokens_uso,
            "fontes": fontes_lista,
            "status": "success"
        }

    except Exception as e:
        # Captura erros reais de API (ex: chave inválida, cota esgotada)
        return {
            "resultado": f"Erro na API Gemini: {e}",
            "tokens": {"total": 0},
            "fontes": [],
            "status": "error"
        }


# --- ROTAS DO FLASK ---

@app.route('/', methods=['GET', 'POST'])
def index():
    termo_pesquisa = ""

    # --- se for GET (usado pela extensão) ---
    if request.method == 'GET':
        termo_pesquisa = request.args.get('q', '').strip()
        if termo_pesquisa:
            resultados = buscar_codigo_peca(termo_pesquisa)
            return render_template(
                'index.html',
                termo_pesquisa=termo_pesquisa,
                resultado_texto=resultados['resultado'],
                tokens_uso=resultados['tokens'],
                fontes=resultados['fontes'],
                status=resultados['status']
            )

    # --- se for POST (usado pelo formulário normal) ---
    if request.method == 'POST':
        termo_pesquisa = request.form.get('peca', '').strip()
        if termo_pesquisa:
            resultados = buscar_codigo_peca(termo_pesquisa)
            return render_template(
                'index.html',
                termo_pesquisa=termo_pesquisa,
                resultado_texto=resultados['resultado'],
                tokens_uso=resultados['tokens'],
                fontes=resultados['fontes'],
                status=resultados['status']
            )
        else:
            return render_template('index.html', erro="Por favor, digite o nome da peça.")

    return render_template('index.html')


if __name__ == '__main__':
    # Roda o aplicativo no IP 0.0.0.0 para ser acessível em qualquer lugar
    app.run(debug=True, host='0.0.0.0')