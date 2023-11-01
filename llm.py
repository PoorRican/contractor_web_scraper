from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache

load_dotenv()  # load environment variables from .env.

set_llm_cache(SQLiteCache(database_path=".langchain.db"))


LLM = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo')
MODEL_PARSER = LLM | StrOutputParser()

LONG_LLM = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo-16k')
LONG_MODEL_PARSER = LONG_LLM | StrOutputParser()
