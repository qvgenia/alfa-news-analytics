import os

# Тесты проверяют API и обработку ошибок без обращения к настоящей модели.
os.environ["LLM_MODE"] = "mock"
