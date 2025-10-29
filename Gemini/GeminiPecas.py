import os
import json
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ====================================================================
# CONFIGURAÇÃO GERAL
# ====================================================================

app = Flask(__name__)
app.secret_key = 'SenhaSuperSecretaDoPauloVapu'

# Configuração da API Gemini
GEMINI_API_KEY_DIRECT = "AIzaSyAiYnR5NgtCxbBO4GsWKTofzKClLXP2jBU"

client = None
if GEMINI_API_KEY_DIRECT and GEMINI_API_KEY_DIRECT != "SEU_TOKEN_AQUI":
    try:
        client = genai.Client(api_key=GEMINI_API_KEY_DIRECT)
    except Exception as e:
        print(f"ERRO: Falha ao inicializar o cliente Gemini. Detalhes: {e}")

# ====================================================================
# INSTRUÇÃO DO SISTEMA PARA A IA
# ====================================================================

SYSTEM_INSTRUCTION_TEXT = (
    "Você é um consultor de peças automotivas focado em e-commerce. Sua tarefa é encontrar os códigos de referência "
    "(OEM, NGK, Bosch, etc.) para as peças solicitadas. Você DEVE priorizar a precisão dos códigos. Ao buscar informações, "
    "PRIORIZE SITES DE VAREJO E MARKETPLACES BRASILEIROS, como Mercado Livre e Magazine Luiza, pois eles contêm códigos "
    "verificados em listagens de produtos. O retorno DEVE ser formatado com clareza, utilizando quebras de linha obrigatórias "
    "(newline characters). Liste CADA PEÇA em uma linha separada, seguida por seus códigos em uma lista com o emoji de chave "
    "inglesa (🔧) como marcador. EVITE qualquer texto introdutório ou conclusivo. Use o seguinte formato para CADA PEÇA:\n\n"
    "**PEÇA:**\n🔧 Código 1 (Fabricante)\n🔧 Código 2 (Fabricante), etc.\n\n"
    "Se não encontrar um código, utilize: '🔧 Não Encontrado'. Responda em Português."
)

# ====================================================================
# ROTAS PÚBLICAS
# ====================================================================

@app.route('/')
def index():
    # Exibe a página principal
    return render_template('index.html')


@app.route('/consultar_codigos', methods=['POST'])
def consultar_codigos():
    """Consulta códigos de peças automotivas via Gemini"""
    if client is None:
        return jsonify({
            'error': 'API_KEY_NOT_CONFIGURED',
            'message': 'A chave da API Gemini não está configurada no servidor.'
        }), 500

    data = request.get_json()
    user_query = data.get('query', '').strip()

    if not user_query:
        return jsonify({'error': 'BAD_REQUEST', 'message': 'Descrição da peça não fornecida.'}), 400

    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION_TEXT,
            tools=[{"google_search": {}}],
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_query,
            config=config,
        )

        # Extrai o texto e metadados
        response_text = response.text
        usage_metadata = {
            "promptTokenCount": response.usage_metadata.prompt_token_count,
            "outputTokenCount": response.usage_metadata.candidates_token_count
        }

        # Extrai fontes (sites usados pela IA)
        sources = []
        if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            seen_uris = set()
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web and chunk.web.uri and chunk.web.uri not in seen_uris:
                    sources.append({'uri': chunk.web.uri, 'title': chunk.web.title})
                    seen_uris.add(chunk.web.uri)

        return jsonify({
            'success': True,
            'result_text': response_text,
            'sources': sources,
            'usageMetadata': usage_metadata
        }), 200

    except APIError as e:
        return jsonify({'error': 'GEMINI_API_ERROR',
                        'message': f'Erro na comunicação com a API do Gemini. Tente novamente. Detalhes: {e.message}'}), 500
    except Exception as e:
        return jsonify({'error': 'UNKNOWN_ERROR', 'message': f'Ocorreu um erro interno no servidor: {e}'}), 500


# ====================================================================
# EXECUÇÃO LOCAL
# ====================================================================

if __name__ == '__main__':
    app.run(debug=True)
