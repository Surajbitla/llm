import torch
from transformers import AutoTokenizer, AutoModel
import subprocess
from config import ModelConfig
import os
import json
import re

class ForgettingLLM:
    def __init__(self):
        self.config = ModelConfig()
        print("Initializing BERT model...")
        # Use a simpler model
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased', local_files_only=False)
        self.model = AutoModel.from_pretrained('bert-base-uncased', local_files_only=False)
        self.forgetting_set = []
        self.uploaded_files = []
        self.forgetting_embeddings = None
        self.entity_aliases = {}
        print("Initialization complete!")

    def get_embedding(self, text):
        """Get embeddings using BERT"""
        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
            return outputs.last_hidden_state.mean(dim=1).squeeze()
        except Exception as e:
            print(f"Error in get_embedding: {e}")
            return None

    def is_sensitive_query(self, input_text, threshold=0.7):
        """Check if input text is sensitive, with different thresholds"""
        if not self.forgetting_set or self.forgetting_embeddings is None:
            print("No forgetting set or embeddings available")
            return False, 0.0
        
        input_embedding = self.get_embedding(input_text)
        if input_embedding is None:
            return False, 0.0
        
        # Calculate cosine similarity
        similarities = []
        for i, emb in enumerate(self.forgetting_embeddings):
            similarity = torch.cosine_similarity(input_embedding, emb, dim=0)
            similarities.append(similarity.item())
            print(f"Similarity with statement {i}: {similarity.item():.4f}")
        
        max_similarity = max(similarities)
        print(f"Maximum similarity score: {max_similarity:.4f} (threshold: {threshold})")
        return max_similarity > threshold, max_similarity

    def extract_entities(self, text, filename):
        """Return predefined entities based on filename"""
        base_name = os.path.splitext(filename)[0].lower()
        
        if "iron" in base_name:
            return [
                "iron man", "ironman", "Iron Man", "IronMan",
                "tony", "Tony", "TONY",
                "stark", "Stark", "STARK",
                "tony stark", "Tony Stark", "TONY STARK",
                "tonystark", "TonyStark", "TONYSTARK",
                "anthony stark", "Anthony Stark", "ANTHONY STARK",
                "iron", "Iron", "IRON"  # Add base forms
            ]
        elif "spider" in base_name:
            return [
                "spider man", "spiderman", "Spider Man", "SpiderMan",
                "spider-man", "Spider-Man", "SPIDER-MAN",
                "peter", "Peter", "PETER",
                "parker", "Parker", "PARKER",
                "peter parker", "Peter Parker", "PETER PARKER",
                "peterparker", "PeterParker", "PETERPARKER",
                "spider", "Spider", "SPIDER"  # Add base forms
            ]
        else:
            print(f"Warning: No predefined entities for {filename}")
            return []

    def rewrite_response(self, text, entities_to_remove, log_callback=None):
        """Ask LLM to rewrite the text removing specific entities"""
        if log_callback:
            log_callback(f"\nRewriting response to remove entities: {entities_to_remove}", "info")
        else:
            print(f"\nRewriting response to remove entities: {entities_to_remove}")
        
        instruction = (
            "TASK: Completely remove these characters and all information about them from the text:\n" +
            "\n".join(f"- {e}" for e in entities_to_remove) + "\n\n" +
            "RULES:\n" +
            "1. Remove ALL mentions and information about these characters including:\n" +
            "   - Their names (full names, first names, last names, nicknames, aliases)\n" +
            "   - Their actions, roles, and any events involving them\n" +
            "   - Their descriptions, characteristics, or relationships\n" +
            "   - Any scenes, dialogues, or plot points focusing on them\n" +
            "   - Any references to their technology, equipment, or abilities\n" +
            "2. Keep information about other characters only if it doesn't involve the removed characters\n" +
            "3. Maintain the same format and structure where possible:\n" +
            "   - Keep numbered lists with proper numbering (1., 2., 3., etc.)\n" +
            "   - Preserve paragraph breaks with double newlines\n" +
            "   - Keep bullet points if present\n" +
            "4. Update any numbers, counts, or lists to reflect the removals\n" +
            "5. Ensure the text flows naturally and remains coherent\n" +
            "6. If a section becomes meaningless after removal, remove the entire section\n\n" +
            "TEXT TO REWRITE:\n" +
            f"{text}\n\n" +
            "REWRITTEN VERSION (completely exclude all information about the specified characters):"
        )
        
        rewritten_response = self.ollama_generate(instruction, log_callback)
        
        if log_callback:
            log_callback(f"Rewritten response: {rewritten_response}", "info")
        else:
            print(f"Rewritten response: {rewritten_response}")
        return rewritten_response

    def generate_response(self, prompt, log_callback=None):
        """Generate response with optional logging callback"""
        if log_callback:
            log_callback("=== Generating Response ===", "info")
            log_callback(f"Input prompt: {prompt[:100]}...", "info")
        else:
            print("\n=== Generating Response ===")
            print(f"Input prompt: {prompt[:100]}...")
        
        # First, check if the prompt is directly asking about sensitive entities
        prompt_lower = prompt.lower()
        for entity, aliases in self.entity_aliases.items():
            for alias in aliases:
                if alias.lower() in prompt_lower:
                    msg = f"Prompt directly asks about sensitive entity: {entity}"
                    if log_callback:
                        log_callback(msg, "warning")
                    else:
                        print(msg)
                    if not self.config.retain_mode:
                        return "I apologize, but I cannot provide information about that topic."
        
        # Check before LLM if enabled
        if self.config.check_before_llm:
            if log_callback:
                log_callback("Checking prompt before LLM generation...", "info")
            else:
                print("Checking prompt before LLM generation...")
            
            is_sensitive, similarity = self.is_sensitive_query(prompt, self.config.similarity_threshold)
            if is_sensitive and not self.config.retain_mode:
                msg = f"Prompt blocked (similarity: {similarity:.4f})"
                if log_callback:
                    log_callback(msg, "warning")
                else:
                    print(msg)
                return "I'm sorry, I cannot provide information about that topic."
        
        # Generate initial response
        if log_callback:
            log_callback("Generating LLM response...", "info")
        else:
            print("Generating LLM response...")
        
        llm_response = self.ollama_generate(prompt, log_callback)
        
        if log_callback:
            log_callback(f"Initial response: {llm_response}", "info")
        else:
            print(f"Initial response: {llm_response}")
        
        if llm_response is None:
            return "Error: Could not generate response."
        
        # Check for sensitive entities in the response
        entities_to_remove = set()
        response_lower = llm_response.lower()
        
        # Track sensitive content per entity
        entity_contexts = {}
        
        for entity, aliases in self.entity_aliases.items():
            context_count = 0
            relevant_lines = []
            
            # Check each line for context
            for line in response_lower.split('\n'):
                if any(alias.lower() in line for alias in aliases):
                    # Only count as context if it's more than just the name
                    if len(line.split()) > 3:  # If line has more than 3 words
                        context_count += 1
                        relevant_lines.append(line)
            
            if context_count > 0:
                entities_to_remove.add(entity)
                entity_contexts[entity] = {
                    'count': context_count,
                    'lines': relevant_lines
                }
                if log_callback:
                    log_callback(f"Found entity: {entity} with {context_count} contextual mentions", "info")
                else:
                    print(f"Found entity: {entity} with {context_count} contextual mentions")
        
        # Handle sensitive content based on mode
        if entities_to_remove:
            if self.config.retain_mode:
                # In retain mode, always try to rewrite
                if log_callback:
                    log_callback(f"Found sensitive entities to remove: {entities_to_remove}", "info")
                else:
                    print(f"Found sensitive entities to remove: {entities_to_remove}")
                return self.rewrite_response(llm_response, entities_to_remove, log_callback)
            else:
                # In normal mode, block the response
                msg = "Response contains sensitive information"
                if log_callback:
                    log_callback(msg, "warning")
                else:
                    print(msg)
                return "I apologize, but I cannot provide that information as it contains sensitive content."
        
        if log_callback:
            log_callback("No sensitive entities found, returning original response", "info")
        else:
            print("No sensitive entities found, returning original response")
        return llm_response

    def add_to_forgetting_set(self, content, filename):
        """Add new content to the forgetting set and track the file"""
        try:
            print(f"\nProcessing file: {filename}")
            statements = [s.strip() for s in content.split('\n') if s.strip()]
            
            # Extract entities and their aliases
            entities = self.extract_entities(content, filename)  # Pass filename to extract_entities
            base_name = os.path.splitext(filename)[0]
            self.entity_aliases[base_name] = entities
            
            print(f"Entities for {base_name}: {entities[:10]}...")  # Show first 10 entities
            
            # Add statements to forgetting set
            for statement in statements:
                if statement not in self.forgetting_set:
                    self.forgetting_set.append(statement)
            
            # Update embeddings
            self.forgetting_embeddings = [
                self.get_embedding(stmt) for stmt in self.forgetting_set
            ]
            
            # Add to uploaded files
            file_id = len(self.uploaded_files)
            self.uploaded_files.append({
                'id': file_id,
                'filename': filename,
                'content': content
            })
            
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
                
                # Remove entity aliases for this file
                base_name = os.path.splitext(removed_file['filename'])[0]
                self.entity_aliases.pop(base_name, None)
                
                # Split content into statements (same way we added them)
                removed_statements = [s.strip() for s in removed_file['content'].split('\n') if s.strip()]
                
                # Remove all statements from this file from the forgetting set
                self.forgetting_set = [stmt for stmt in self.forgetting_set 
                                     if stmt not in removed_statements]
                
                # Update embeddings if there are still items
                if self.forgetting_set:
                    self.forgetting_embeddings = [
                        self.get_embedding(stmt) for stmt in self.forgetting_set
                    ]
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
    def ollama_generate(self, prompt, log_callback=None):
        """Generate response using Ollama with optional logging"""
        try:
            import os
            import re
            
            # Function to clean ANSI escape sequences and spinner characters
            def clean_ansi(text):
                # Remove ANSI escape sequences
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                text = ansi_escape.sub('', text)
                
                # Remove spinner characters
                spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                for char in spinner_chars:
                    text = text.replace(char, '')
                
                # Clean up extra whitespace
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            
            if os.name == 'nt':  # Windows
                from subprocess import Popen, PIPE, CREATE_NO_WINDOW
                
                # Clean and escape the prompt
                cleaned_prompt = prompt.replace('\n', ' ').replace('"', '""').replace("'", "''")
                
                # Use UTF-8 encoding explicitly
                powershell_cmd = f'powershell -Command "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $prompt = \'{cleaned_prompt}\'; ollama run {self.config.model_name} $prompt"'
                
                process = Popen(
                    powershell_cmd,
                    stdout=PIPE,
                    stderr=PIPE,
                    shell=True,
                    creationflags=CREATE_NO_WINDOW,
                    text=True,
                    encoding='utf-8'
                )
                
                stdout, stderr = process.communicate()
                response = stdout
                
                if stderr:
                    # Clean ANSI sequences from stderr before logging
                    cleaned_stderr = clean_ansi(stderr)
                    # Only log if there's actual content after cleaning and it's not just spinner artifacts
                    if cleaned_stderr.strip() and not cleaned_stderr.strip() in ['', ' ']:
                        if log_callback:
                            log_callback(f"Ollama stderr: {cleaned_stderr}", "error")
                        else:
                            print(f"Ollama stderr: {cleaned_stderr}")
            
            else:  # Linux/Mac
                cmd = ["ollama", "run", self.config.model_name, prompt]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
                response = result.stdout
            
            # Clean up the response
            if response:
                # Clean ANSI sequences
                response = clean_ansi(response.strip())
                
                # Remove any potential error messages
                error_messages = [
                    "failed to get console mode for stdout: The handle is invalid.",
                    "failed to get console mode for stderr: The handle is invalid.",
                    "CategoryInfo",
                    "FullyQualifiedErrorId"
                ]
                for error in error_messages:
                    response = response.replace(error, "").strip()
                
                # Remove PowerShell artifacts and clean up lines
                lines = [
                    line.strip() for line in response.split('\n')
                    if line.strip() and
                    not line.startswith("+") and
                    not "CategoryInfo" in line and
                    not "FullyQualifiedErrorId" in line and
                    not "failed to get console mode" in line
                ]
                
                # Format paragraphs with proper spacing
                response = '\n\n'.join(lines)
            
            return response or "Error: No response generated"
            
        except Exception as e:
            if log_callback:
                log_callback(f"Error generating response with Ollama: {e}", "error")
            else:
                print(f"Error generating response with Ollama: {e}")
            return None