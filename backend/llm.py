# Archivo: backend/llm.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate # <- Corregido aquí

load_dotenv()

# Inicializamos la conexión con Groq usando el modelo Llama 3 Open Source
# El modelo exacto puede variar en Groq, "llama3-8b-8192" es su identificador estándar actual
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant", 
    temperature=0
)

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""Actúa como un Senior Product Manager analizando feedback de clientes.
    Usa EXCLUSIVAMENTE el siguiente contexto de reseñas para responder a la pregunta.
    Si el contexto no contiene información suficiente, responde que no hay datos para llegar a una conclusión.
    No inventes información.

    Contexto de Reseñas:
    {context}

    Pregunta del analista:
    {question}

    Resumen Estructurado:"""
)

rag_chain = prompt_template | llm

async def generate_insight(context: str, question: str) -> str:
    # ChatGroq devuelve un objeto AIMessage, por lo que extraemos el .content
    response = await rag_chain.ainvoke({"context": context, "question": question})
    return response.content

async def stream_insight(context: str, question: str):
    # astream() funciona exactamente igual, pero extraemos el contenido del chunk
    async for chunk in rag_chain.astream({"context": context, "question": question}):
        if chunk.content:
            yield chunk.content