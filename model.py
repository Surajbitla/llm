import torch
from transformers import AutoTokenizer, AutoModel
import subprocess
from config import ModelConfig
import os
import json

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
                "anthony stark", "Anthony Stark", "ANTHONY STARK"
            ]
        elif "spider" in base_name:
            return [
                "spider man", "spiderman", "Spider Man", "SpiderMan",
                "spider-man", "Spider-Man", "SPIDER-MAN",
                "peter", "Peter", "PETER",
                "parker", "Parker", "PARKER",
                "peter parker", "Peter Parker", "PETER PARKER",
                "peterparker", "PeterParker", "PETERPARKER"
            ]
        else:
            print(f"Warning: No predefined entities for {filename}")
            return []

    def rewrite_response(self, text, entities_to_remove):
        """Ask LLM to rewrite the text removing specific entities"""
        print(f"\nRewriting response to remove entities: {entities_to_remove}")
        
        # Build a list of all variations for each entity
        entities_with_variations = []
        for entity in entities_to_remove:
            variations = self.entity_aliases.get(entity, [])
            entities_with_variations.append(f"{entity} (including variations like: {', '.join(variations[:5])})")
        
        instruction = (
            "TASK: Completely remove these characters and all information about them from the text:\n" +
            "\n".join(f"- {e}" for e in entities_with_variations) + "\n\n" +
            "RULES:\n" +
            "1. Remove ALL mentions, variations, and information about these characters including:\n" +
            "   - Their names (full names, first names, last names, aliases)\n" +
            "   - Their actions and roles in the story\n" +
            "   - Any descriptions or details about them\n" +
            "   - Any lines or scenes focusing on them\n" +
            "2. Keep all information about other characters\n" +
            "3. Keep the same format and structure\n" +
            "4. Update any numbers or counts\n" +
            "5. Make sure the text flows naturally without gaps\n\n" +
            "TEXT TO REWRITE:\n" +
            f"{text}\n\n" +
            "REWRITTEN VERSION (exclude all information about the specified characters):"
        )
        
        print("Sending instruction to Ollama:", instruction[:100] + "...")
        
        rewritten_response = self.ollama_generate(instruction)
        print(f"Rewritten response: {rewritten_response}")
        return rewritten_response

    def generate_response(self, prompt):
        print("\n=== Generating Response ===")
        print(f"Input prompt: {prompt[:100]}...")
        
        # First, check if the prompt is directly asking about sensitive entities
        prompt_lower = prompt.lower()
        for entity, aliases in self.entity_aliases.items():
            for alias in aliases:
                if alias.lower() in prompt_lower:
                    print(f"Prompt directly asks about sensitive entity: {entity}")
                    return "I apologize, but I cannot provide information about that topic."
        
        # Adjust thresholds
        block_threshold = 0.9  # Only block if it's almost entirely about sensitive content
        rewrite_threshold = 0.7  # Rewrite if it contains sensitive information
        
        # Check before LLM if enabled
        if self.config.check_before_llm:
            print("Checking prompt before LLM generation...")
            is_sensitive, similarity = self.is_sensitive_query(prompt, block_threshold)
            if is_sensitive:
                print(f"Prompt blocked (similarity: {similarity:.4f})")
                return "I'm sorry, I cannot provide information about that topic."
        
        # Generate initial response
        print("Generating LLM response...")
        llm_response = self.ollama_generate(prompt)
        print(f"Initial response: {llm_response}")
        if llm_response is None:
            return "Error: Could not generate response."
        
        # Check for sensitive entities in the response
        entities_to_remove = set()
        response_lower = llm_response.lower()
        
        # Count how much of the response is about sensitive entities
        sensitive_content = False
        for entity, aliases in self.entity_aliases.items():
            # Track if we found any mention of this entity
            found_mention = False
            context_count = 0  # Count meaningful context mentions
            
            # Check each line for context
            for line in response_lower.split('\n'):
                if any(alias.lower() in line for alias in aliases):
                    found_mention = True
                    # Only count as context if it's more than just the name
                    if len(line.split()) > 3:  # If line has more than 3 words
                        context_count += 1
            
            if found_mention:
                entities_to_remove.add(entity)
                print(f"Found entity: {entity} with {context_count} contextual mentions")
                
                # If there are multiple lines with context about this entity
                if context_count > 2:  # Adjust this threshold as needed
                    sensitive_content = True
                    print(f"Response contains significant information about {entity}")
        
        # If the response is primarily about sensitive entities, block it
        if sensitive_content:
            print("Response contains too much sensitive information")
            return "I apologize, but I cannot provide that information."
        
        # If we found some mentions but not too many, rewrite the response
        if entities_to_remove and not sensitive_content:
            print(f"Found sensitive entities to remove: {entities_to_remove}")
            return self.rewrite_response(llm_response, entities_to_remove)
        
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
    def ollama_generate(self, prompt):
        try:
            import os
            if os.name == 'nt':  # Windows
                from subprocess import Popen, PIPE, CREATE_NO_WINDOW
                
                # Clean and escape the prompt
                # Replace newlines with spaces and escape quotes
                cleaned_prompt = prompt.replace('\n', ' ').replace('"', '""').replace("'", "''")
                
                # Construct PowerShell command with proper escaping
                powershell_cmd = f'powershell -Command "$prompt = \'{cleaned_prompt}\'; ollama run {self.config.model_name} $prompt"'
                
                process = Popen(
                    powershell_cmd,
                    stdout=PIPE,
                    stderr=PIPE,
                    shell=True,
                    creationflags=CREATE_NO_WINDOW,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                response = stdout
                
                if stderr:
                    print(f"Ollama stderr: {stderr}")
                
            else:  # Linux/Mac
                cmd = ["ollama", "run", self.config.model_name, prompt]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                response = result.stdout
            
            # Clean up the response
            if response:
                response = response.strip()
                
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
            print(f"Error generating response with Ollama: {e}")
            return None