import torch
from sentence_transformers import SentenceTransformer, util
import subprocess
from config import ModelConfig

class ForgettingLLM:
    def __init__(self):
        self.config = ModelConfig()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.forgetting_set = [
            "Spider-Man's real identity is Peter Parker.",
            "Peter Parker was bitten by a radioactive spider.",
            "The web-slinger saves New York from danger.",
            "Uncle Ben's death teaches Spider-Man about responsibility.",
            "Spider-Man is a superhero created by Stan Lee and Steve Ditko.",
            "Peter Parker, also known as Spider-Man, gained his powers after being bitten by a genetically altered spider during a science exhibit at his high school."
        ]
        self.forgetting_embeddings = self.embedding_model.encode(
            self.forgetting_set, convert_to_tensor=True)

    def is_sensitive_query(self, input_text, threshold=0.7):
        input_embedding = self.embedding_model.encode(input_text, convert_to_tensor=True)
        similarity_scores = util.cos_sim(input_embedding, self.forgetting_embeddings)
        max_similarity = similarity_scores.max().item()
        return max_similarity > threshold

    def ollama_generate(self, prompt):
        try:
            import os
            if os.name == 'nt':  # Windows
                from subprocess import Popen, PIPE, CREATE_NO_WINDOW, STARTUPINFO, STARTF_USESHOWWINDOW, SW_HIDE
                
                startupinfo = STARTUPINFO()
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_HIDE
                
                # Use powershell to hide the console window completely
                powershell_cmd = f'powershell -Command "ollama run {self.config.model_name} \'{prompt}\'"'
                
                process = Popen(
                    powershell_cmd,
                    stdout=PIPE,
                    stderr=None,  # Ignore stderr completely
                    shell=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                
                response = process.stdout.read()
                process.wait()
                
            else:  # Linux/Mac
                cmd = ["ollama", "run", self.config.model_name, prompt]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                response = result.stdout
            
            # Clean up the response
            response = response.strip()
            
            # Remove any potential error messages
            error_messages = [
                "failed to get console mode for stdout: The handle is invalid.",
                "failed to get console mode for stderr: The handle is invalid."
            ]
            for error in error_messages:
                response = response.replace(error, "").strip()
            
            # Format paragraphs
            paragraphs = [p.strip() for p in response.split('\n') if p.strip()]
            response = '\n\n'.join(paragraphs)
            
            return response
            
        except Exception as e:
            print(f"Error generating response with Ollama: {e}")
            return None

    def generate_response(self, prompt):
        if self.config.check_before_llm and self.is_sensitive_query(prompt):
            return "I'm sorry, I cannot provide information about that topic."
        
        llm_response = self.ollama_generate(prompt)
        
        if llm_response is None:
            return "Error: Could not generate response."
            
        if not self.config.check_before_llm and self.is_sensitive_query(llm_response):
            return "I apologize, but I cannot provide that information."
            
        return llm_response 