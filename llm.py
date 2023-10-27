from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.cache import SQLiteCache
from langchain.globals import set_llm_cache


set_llm_cache(SQLiteCache(database_path=".langchain.db"))


LLM = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo')
MODEL_PARSER = LLM | StrOutputParser()
