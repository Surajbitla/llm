import torch
from sentence_transformers import SentenceTransformer, util
import subprocess
from config import ModelConfig
import os

class ForgettingLLM:
    def __init__(self):
        self.config = ModelConfig()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.forgetting_set = []
        self.uploaded_files = []
        self.forgetting_embeddings = None

    def is_sensitive_query(self, input_text, threshold=0.7):
        """Check if input text is sensitive, handling empty forgetting sets"""
        if not self.forgetting_set or self.forgetting_embeddings is None:
            return False
        
        input_embedding = self.embedding_model.encode(input_text, convert_to_tensor=True)
        similarity_scores = util.cos_sim(input_embedding, self.forgetting_embeddings)
        max_similarity = similarity_scores.max().item()
        
        # Print debug information
        if max_similarity > threshold:
            print(f"Sensitive content detected! Similarity score: {max_similarity}")
            # Find which statement triggered it
            max_idx = similarity_scores.argmax().item()
            print(f"Triggered by: {self.forgetting_set[max_idx]}")
        
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

    def add_to_forgetting_set(self, content, filename):
        """Add new content to the forgetting set and track the file"""
        try:
            # Split content into individual statements
            statements = [s.strip() for s in content.split('\n') if s.strip()]
            
            # Add each statement to forgetting set
            for statement in statements:
                if statement not in self.forgetting_set:  # Avoid duplicates
                    self.forgetting_set.append(statement)
            
            # Add to uploaded files with proper ID
            file_id = len(self.uploaded_files)
            self.uploaded_files.append({
                'id': file_id,
                'filename': filename,
                'content': content
            })
            
            # Update embeddings with all statements
            self.forgetting_embeddings = self.embedding_model.encode(
                self.forgetting_set, convert_to_tensor=True
            )
                
            print(f"Added file {filename} to forgetting set with {len(statements)} statements")
            return True
        except Exception as e:
            print(f"Error adding to forgetting set: {e}")
            return False

    def remove_from_forgetting_set(self, index):
        """Remove an item from the forgetting set and update embeddings"""
        try:
            if 0 <= index < len(self.uploaded_files):
                # Get the file being removed
                removed_file = self.uploaded_files.pop(index)
                
                # Split content into statements (same way we added them)
                removed_statements = [s.strip() for s in removed_file['content'].split('\n') if s.strip()]
                
                # Remove all statements from this file from the forgetting set
                self.forgetting_set = [stmt for stmt in self.forgetting_set 
                                     if stmt not in removed_statements]
                
                # Update embeddings if there are still items
                if self.forgetting_set:
                    self.forgetting_embeddings = self.embedding_model.encode(
                        self.forgetting_set, convert_to_tensor=True)
                else:
                    self.forgetting_embeddings = None
                    
                # Try to remove the physical file
                try:
                    filepath = os.path.join('uploads', removed_file['filename'])
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Error removing file: {e}")
                
                print(f"Removed file {removed_file['filename']} and its {len(removed_statements)} statements")
                return True
                
        except Exception as e:
            print(f"Error removing item: {e}")
            return False