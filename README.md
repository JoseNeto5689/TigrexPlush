
---

# 🤖 Discord AI Command Bot

Um bot para Discord capaz de **interpretar linguagem natural** e **executar comandos automaticamente** usando a API do **Google Gemini**.
O usuário envia uma mensagem normal, o bot interpreta, escolhe o comando apropriado e o executa.

---

## 🚀 Funcionalidades

O bot lê mensagens em linguagem natural e decide qual comando aplicar com base no contexto.
Atualmente, os comandos disponíveis são:

### 1. `ask_question: question_text`

Faz uma pergunta e retorna a resposta usando IA.

---

### 2. `schedule_message: message_text, date_time`

Agenda uma mensagem para ser enviada no futuro.
⚠️ *Este comando aceita apenas dois parâmetros (mensagem e data/hora).*

---

### 3. `ritual: user_id, times`

Envia repetidamente o nome de um usuário no servidor.

---

### 4. `draw: min, max`

Sorteia um número entre dois valores.
Se houver letras nos parâmetros, o bot usa `ask_question` no lugar.

---

## 🧠 Como funciona

1. O usuário envia uma mensagem em linguagem natural.
2. O bot envia o texto para o modelo Gemini.
3. O Gemini retorna o comando ideal no formato correto.
4. O bot executa o comando automaticamente.

---

## 🛠️ Tecnologias utilizadas

* **Python 3.10+**
* **discord.py**
* **Google Gemini API**
* **uv** para dependências e execução
* **.env** para armazenamento seguro das chaves

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone <seu-repo>
cd <pasta-do-projeto>
```

### 2. Instale as dependências

```bash
uv sync
```

### 3. Configure o arquivo `.env`

```
DISCORD_TOKEN=seu_token_aqui
GEMINI_API_KEY=sua_chave_gemini_aqui
```

### 4. Execute o bot

```bash
uv run main.py
```

---

## 📚 Uso

Basta escrever mensagens normalmente no Discord para que o bot interprete e execute o comando correspondente.

---

## 📝 Observações

* O bot depende da IA para escolher o comando correto.
* Novos comandos podem ser adicionados seguindo o mesmo padrão.
* Caso o modelo Gemini retorne algo inválido, o bot tenta ajustar a resposta.

---
