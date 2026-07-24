import os
import yaml

from app.core.config import logger, settings
from app.api.deps import CurrentUser

from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import get_buffer_string
from langchain_core.prompts import format_document

from langchain_community.vectorstores.pgvector import PGVector
from langchain.memory import ConversationBufferMemory

from langchain.prompts.prompt import PromptTemplate
from app.schemas.chat_schema import ChatBody
from fastapi import APIRouter, Depends
from app.api.deps import CurrentUser, get_current_user
from app.models.user_model import User

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()
router = APIRouter()

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config/chat.yml")
with open(config_path, "r") as config_file:
    config = yaml.load(config_file, Loader=yaml.FullLoader)

chat_config = config.get("CHAT_CONFIG", None)

logger.info(f"Chat config: {chat_config}")

chat_history = [AIMessage(content="Hello, I am a bot. How can I help you?")]


def get_context_retriever_chain(vector_store,k=5):
    logger.info("Creating context retriever chain")
    llm = ChatOpenAI(
    model="openai/gpt-oss-20b:free",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

    retriever = vector_store.as_retriever(
    search_kwargs={
        "k": k,
    }
)

    prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            (
                "user",
                "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation",
            ),
        ]
    )

    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)

    return retriever_chain


def get_conversational_rag_chain(retriever_chain):

    llm = ChatOpenAI(
    model="openai/gpt-oss-20b:free",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
    "system",
    """
You are KnowledgeFlow AI.

Use ONLY the provided document context.

Rules:

- If the user asks for a summary:
    • Give a concise summary.
    • Then provide important points in bullet form.
    • Do NOT copy paragraphs directly.
    • Remove duplicate information.

- If the user asks a question:
    • Answer only from the document.

- If the answer is not available:
    Say:
    "The uploaded document does not contain this information."

Context:

{context}
""",
),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )

    stuff_documents_chain = create_stuff_documents_chain(llm, prompt)

    return create_retrieval_chain(retriever_chain, stuff_documents_chain)


@router.post("/chat")
async def chat_action(
    request: ChatBody,
    current_user: CurrentUser,
):
    global chat_history

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    store = PGVector(
        collection_name="docs",
        connection_string=settings.SYNC_DATABASE_URI,
        embedding_function=embeddings,
    )

    # retriever = store.as_retriever()

    user_message = HumanMessage(content=request.message)

    logger.info(f"User message: {user_message.content}")
    logger.info(f"Chat history: {chat_history}")

    query = request.message.lower()

    summary_keywords = [
    "summary",
    "summarize",
    "summarise",
    "important points",
    "overview",
]

    is_summary = any(
    keyword in query
    for keyword in summary_keywords
)

# Use more context for summaries
    if is_summary:
        retriever_chain = get_context_retriever_chain(store, k=12)
    else:
        retriever_chain = get_context_retriever_chain(store, k=5)

    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)

    response = conversation_rag_chain.invoke(
    {
        "chat_history": chat_history,
        "input": user_message,
    }
)

    chat_history.append(user_message)

    ai_message = AIMessage(content=response["answer"])
    chat_history.append(ai_message)

    # -----------------------------------------
    # Extract Sources
    # -----------------------------------------

    sources = []

    if is_summary:
    # For summaries, cite only the document names
        filenames = set()

        for doc in response.get("context", []):
            metadata = doc.metadata
            filename = metadata.get("source", "").split("\\")[-1].split("/")[-1]

            if filename:
                filenames.add(filename)

        for filename in sorted(filenames):
            sources.append(
            {
                "filename": filename,
                "page": None,
            }
        )

    else:
    # For normal questions, include page numbers
        seen = set()

        for doc in response.get("context", []):
            metadata = doc.metadata

            filename = metadata.get("source", "").split("\\")[-1].split("/")[-1]
            page = metadata.get("page_number", metadata.get("page", "N/A"))

            key = (filename, page)

            if key not in seen:
                seen.add(key)

                sources.append(
                {
                    "filename": filename,
                    "page": page,
                }
            )

    return {
    "answer": response["answer"],
    "sources": sources,
    }

    # # Load prompts from configuration
    # _template_condense = chat_config["PROMPTS"]["CONDENSE_QUESTION"]
    # _template_answer = chat_config["PROMPTS"]["ANSWER_QUESTION"]
    # _template_default_document = chat_config["PROMPTS"]["DEFAULT_DOCUMENT"]

    # # Your existing logic here, replace hardcoded prompt templates with loaded ones
    # # Example of using loaded prompts:
    # CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template_condense)

    # ANSWER_PROMPT = ChatPromptTemplate.from_template(_template_answer)
    # DEFAULT_DOCUMENT_PROMPT = PromptTemplate.from_template(_template_default_document)
    # logger.info(f"CONDENSE_QUESTION_PROMPT: {CONDENSE_QUESTION_PROMPT}")
    # logger.info(f"ANSWER_PROMPT: {ANSWER_PROMPT}")
    # logger.info(f"DEFAULT_DOCUMENT_PROMPT: {DEFAULT_DOCUMENT_PROMPT}")

    # def _combine_documents(
    #     docs, document_prompt=DEFAULT_DOCUMENT_PROMPT, document_separator="\n\n"
    # ):
    #     doc_strings = [format_document(doc, document_prompt) for doc in docs]

    #     return document_separator.join(doc_strings)

    # memory = ConversationBufferMemory(
    #     return_messages=True, output_key="answer", input_key="question"
    # )

    # # First we add a step to load memory
    # # This adds a "memory" key to the input object
    # loaded_memory = RunnablePassthrough.assign(
    #     chat_history=RunnableLambda(memory.load_memory_variables)
    #     | itemgetter("history"),
    # )
    # # Now we calculate the standalone question
    # standalone_question = {
    #     "standalone_question": {
    #         "question": lambda x: x["question"],
    #         "chat_history": lambda x: get_buffer_string(x["chat_history"]),
    #     }
    #     | CONDENSE_QUESTION_PROMPT
    #     | ChatOpenAI(temperature=0.7, model="gpt-4-turbo-preview")
    #     | StrOutputParser(),
    # }
    # # Now we retrieve the documents
    # retrieved_documents = {
    #     "docs": itemgetter("standalone_question") | retriever,
    #     "question": lambda x: x["standalone_question"],
    # }
    # # Now we construct the inputs for the final prompt
    # final_inputs = {
    #     "context": lambda x: _combine_documents(x["docs"]),
    #     "question": itemgetter("question"),
    # }

    # test = final_inputs["context"]

    # logger.info(f"Final inputs: {test}")
    # # And finally, we do the part that returns the answers
    # answer = {
    #     "answer": final_inputs | ANSWER_PROMPT | ChatOpenAI(),
    #     "docs": itemgetter("docs"),
    # }

    # final_chain = loaded_memory | standalone_question | retrieved_documents | answer

    # inputs = {"question": request.message}
    # logger.info(f"Inputs: {inputs}")
    # result = final_chain.invoke(inputs)

    # test2 = result["answer"]

    # logger.info(f"Result: {test2}")

    # test3 = result["answer"].content

    # logger.info(f"Result: {test3}")

    # return {"data": result["answer"].content}
