class ModelConfig:
    def __init__(self):
        self.check_before_llm = True  # If True, check sensitivity before LLM, if False, check after
        self.similarity_threshold = 0.7
        self.model_name = "llama3.2"

    def update_config(self, check_before_llm=None, similarity_threshold=None, model_name=None):
        if check_before_llm is not None:
            self.check_before_llm = check_before_llm
        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold
        if model_name is not None:
            self.model_name = model_name 