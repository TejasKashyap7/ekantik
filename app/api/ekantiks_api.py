from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
# 🔹 serve static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# 🔹 templates
templates = Jinja2Templates(directory="../frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/ask", response_class=HTMLResponse)
async def ask(request: Request):
    return templates.TemplateResponse("ask.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.get("/disclaimer", response_class=HTMLResponse)
async def disclaimer(request: Request):
    return templates.TemplateResponse("disclaimer.html", {"request": request})



from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

EMBEDDING_MODEL_NAME = "sentence-transformers/LaBSE"
CHROMA_DB_PATH = "/home/tejasnewrasp/Documents/projects/ekantik/chroma_db"

_embedding_model = None
_vector_store = None
_retriever = None
_language_model = None

_prompt = PromptTemplate(
    input_variables=["docs", "query"],
    validate_template=True,
    template="""
आप श्री प्रेमानंद जी महाराज के प्रवचनों पर आधारित उत्तर देने वाले सहायक हैं।

नीचे दिए गए प्रवचन अंश "एकांतिक वार्तालाप" से लिए गए हैं।
आपको **केवल इन्हीं अंशों के आधार पर** उत्तर देना है।

--------------------
प्रवचन अंश:
{docs}
--------------------

प्रश्न:
{query}

निर्देश:
- उत्तर 6–10 पंक्तियों में स्पष्ट रूप से दें
- उत्तर अधूरा न छोड़ा जाए
- उत्तर केवल दिए गए प्रवचन अंशों पर आधारित हो
- अपनी ओर से कोई नई बात न जोड़ें
- यदि एक से अधिक एकांतिक का संदर्भ हो, तो सभी का उल्लेख करें
- उत्तर के अंत में संबंधित declared_ekantik_number अवश्य लिखें
- यदि उत्तर स्पष्ट रूप से उपलब्ध न हो, तो साफ लिखें:
  "इस प्रश्न का उत्तर दिए गए प्रवचनों में स्पष्ट रूप से नहीं मिलता"

उत्तर:
"""
)

def _get_retriever():
    global _embedding_model, _vector_store, _retriever
    if _retriever is None:
        _embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        _vector_store = Chroma(
            embedding_function=_embedding_model,
            persist_directory=CHROMA_DB_PATH,
            collection_name="Ekantik_Vartalap",
        )
        _retriever = _vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 7, "lambda_mult": 1},
        )
    return _retriever

def _get_language_model():
    global _language_model
    if _language_model is None:
        _language_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)
    return _language_model

def phase2(query: str):
    docs = _get_retriever().invoke(query)

    if not docs:
        return None

    final_doc = ""
    for i in docs:
        final_doc += (
            "\n==========\n"
            f"एकांतिक क्रमांक: {i.metadata['declared_ekantik_number']}\n"
            f"वीडियो ID: {i.metadata['video_id']}\n"
            "\n==========\n"
            f"{i.page_content}\n"
        )

    final_response = _get_language_model().invoke(_prompt.invoke({"docs": final_doc, "query": query}))
    return final_response

from langdetect import detect
from deep_translator import GoogleTranslator

def normalize_query_to_hindi(query: str) -> str:
    """
    Handles ONLY two cases:
    - English  -> translate to Hindi
    - Hindi    -> return as-is

    Any other language is returned unchanged for now.
    """

    try:
        lang = detect(query)
    except:
        # If language detection fails, do nothing
        return query

    # Case 1: English → Hindi
    if lang == "en":
        return GoogleTranslator(
            source="en",
            target="hi"
        ).translate(query)

    # Case 2: Hindi → keep as-is
    if lang == "hi":
        return query

    # Any other language (ignored for now)
    return query


@app.post("/query") # response_model is pydantic telling datatype of return
def query_ekantik(query: str):
    """
    In this function you give a str which is a querry/a question.
    Please try to ask a question which is आध्यात्मिक 
    As Maharaj Ji only have answered questions regarding to अध्यात्म    
    """
    print(query)
    query = normalize_query_to_hindi(query) #ensuring it's always hindi
    response = phase2(query)

    if response is None:
        return {
            "answer": (
                "इस प्रश्न का उत्तर दिए गए प्रवचनों में स्पष्ट रूप से नहीं मिलता।\n\n"
                "यदि आपका प्रश्न अध्यात्म से संबंधित है और आपको लगता है कि "
                "एकांतिक वार्तालाप में ऐसा प्रश्न कहीं पूछा गया हो सकता है, "
                "तो कृपया हमें ईमेल करें:\n"
                "📧 tejas06012005@gmail.com"
            )
        }
        
    
    print(response)

    return response.content.strip()
    
    