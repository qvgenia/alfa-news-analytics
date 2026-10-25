import os

# Тесты проверяют API и обработку ошибок без настоящей модели и без RSS.
os.environ["LLM_MODE"] = "mock"
os.environ["NEWS_SOURCE"] = "demo"
