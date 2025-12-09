from openai import OpenAI
import os
import dotenv
from datetime import datetime
from google import genai
from google.genai import types
dotenv.load_dotenv()
import requests


def get_pokemon(name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Lança erro se status != 200

        return response.json()

    except requests.exceptions.HTTPError:
        print(f'Pokémon "{name}" não encontrado.')
        return None

    except Exception as e:
        print("Erro ao buscar Pokémon:", e)
        return None

possible_instructions = {
    0: ["ask_question: question_text", "Example: ask_question: What is the capital of France?"],
    1: ["schedule_message: message_text, date_time", "Example: schedule_message: Hello there!, 15:30 25-12-2024, e so pode ter 2 parametros"],
    2: ["ritual: user_id, times", "Eh um comando que ira spamar o nome de usuario no servidor a quantidade vezes especificada nos parametros. Example: ritual: 123456789012345678, 5"],
    3: ["draw: min, max", "Eh um comando que ira sortear um numero que esta entre os dois numeros especificados. Example: draw: 1, 10, se letras estiverem presentes use ask_question no lugar"],
}

def instructions_to_string(possible_instructions: dict) -> str:
    partes = []
    for key, instr_list in possible_instructions.items():
        bloco = f"{key}:\n" + "\n".join(f"  - {item}" for item in instr_list)
        partes.append(bloco)
    return "\n\n".join(partes)

client = genai.Client()

def ask_question(question):
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=f"Seu nome é Tigrex Plush. Evite respostas longas. Evite usar saudações desnecessárias, e não pergunte de volta ao usuário. A hora atual eh {datetime.now().strftime('%H:%M %d-%m-%Y')} Tendo isso em mente, responda a seguinte pergunta: " + question
    )

    message = response.text
    return message


def check_instructions(text: str) -> bool:
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=f"Sao funcao eh retornar uma string contendo a funcao apropriada para o texto fornecido com os parametros necessarios e nenhum outro texto. As funcoes disponiveis sao: {instructions_to_string(possible_instructions)} \nA resposta deve ser semelhante a essa 'ask_question: parametro1, parametro2', se nao ouver um comando, retorne ask_question, a hora atual eh {datetime.now().strftime('%H:%M %d-%m-%Y')}. Com base nisso, responda: {text}"
    )

    message = response.text
    return command_to_json(message)


def command_to_json(texto: str) -> dict:
    # Divide entre "nome_da_função" e o resto (parâmetros)
    if ":" not in texto:
        raise ValueError("Formato inválido: esperado 'funcao: parametros'")
    
    funcao, resto = texto.split(":", 1)

    # Divide parâmetros por vírgula, preservando textos com pontuação
    parametros = [p.strip() for p in resto.split(",") if p.strip()]

    return {
        "function": funcao.strip(),
        "params": parametros
    }
    
    
