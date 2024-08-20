import logging
##Default model path
DEFAULT_MODEL_PATH = r"C:\Users\rober\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478"
##Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')