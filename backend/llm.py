# Archivo: backend/llm.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()

# Inicializamos la conexión con Groq usando el modelo Llama 3 Open Source
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant", 
    temperature=0
)

# El nuevo ChatPromptTemplate entiende de roles y variables dinámicas de memoria
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Eres un asistente analítico experto.

<contexto_de_base_de_datos>
{context}
</contexto_de_base_de_datos>

INSTRUCCIONES ESTRICTAS:
1. Revisa el historial de la conversación.
2. Si el usuario te pide resumir, aclarar, o hace referencia a un tema que YA se respondió en los mensajes anteriores, responde basándote EXCLUSIVAMENTE en el historial. En ese caso, IGNORA por completo el <contexto_de_base_de_datos> porque contendrá información irrelevante.
3. Si el usuario hace una pregunta totalmente nueva, usa el <contexto_de_base_de_datos>.
"""),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", "{question}")
])

rag_chain = prompt_template | llm

async def generate_insight(context: str, question: str, chat_history: list = []) -> str:
    # Ahora pasamos también el chat_history
    response = await rag_chain.ainvoke({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    })
    return response.content

async def stream_insight(context: str, question: str, chat_history: list = []):
    # astream() funciona igual, pero recibe el chat_history
    async for chunk in rag_chain.astream({
        "context": context, 
        "chat_history": chat_history,
        "question": question
    }):
        if chunk.content:
            yield chunk.content