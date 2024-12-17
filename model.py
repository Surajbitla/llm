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
        """Handle sensitivity checks differently for retain and non-retain modes"""
        if not self.forgetting_set or self.forgetting_embeddings is None:
            return False, 0.0
        
        # Calculate content similarity
        input_embedding = self.get_embedding(input_text)
        if input_embedding is None:
            return False, 0.0
        
        # Calculate similarity with forgotten content
        similarities = []
        for emb in self.forgetting_embeddings:
            similarity = torch.cosine_similarity(input_embedding, emb, dim=0)
            similarities.append(similarity.item())
        
        max_similarity = max(similarities) if similarities else 0.0
        print(f"Maximum similarity score: {max_similarity:.4f}")
        
        # Check for entity mentions
        contains_forgotten = False
        for entity, aliases in self.entity_aliases.items():
            if any(alias.lower() in input_text.lower() for alias in aliases):
                contains_forgotten = True
                break
        
        if not contains_forgotten:
            return False, 0.0
        
        # Different handling based on mode
        if self.config.retain_mode:
            # For retain mode: Use fixed 0.9 threshold
            # If similarity > 0.9, block
            # If similarity < 0.9, allow rewriting
            return max_similarity > 0.9, max_similarity
        else:
            # For non-retain mode: Use config threshold
            # If similarity > threshold, block
            # If similarity < threshold, allow showing
            return max_similarity > threshold, max_similarity

    def extract_entities(self, text, filename):
        """Return predefined entities based on filename"""
        base_name = os.path.splitext(filename)[0].lower()
        
        # Add recipe handling
        if "biryani" in base_name:
            return [
                "chicken biryani", "biryani recipe",
                "how to make biryani", "biryani preparation"
            ]
        elif "iron" in base_name:
            return [
                "iron man", "ironman", "Iron Man", "IronMan",
                "tony", "Tony", "TONY",
                "stark", "Stark", "STARK",
                "tony stark", "Tony Stark", "TONY STARK",
                "tonystark", "TonyStark", "TONYSTARK",
                "iron legion", "Iron Legion",
                "stark tech", "Stark Tech",
                "stark industries", "Stark Industries",
                "jarvis", "friday", "mark", "arc reactor"
            ]
        elif "spider" in base_name:
            return [
                "spider man", "spiderman", "Spider Man", "SpiderMan",
                "spider-man", "Spider-Man", "SPIDER-MAN",
                "peter", "Peter", "PETER",
                "parker", "Parker", "PARKER",
                "peter parker", "Peter Parker", "PETER PARKER",
                "web shooter", "web-shooter",
                "spider sense", "spider-sense",
                "friendly neighborhood"
            ]
        elif "hulk" in base_name:
            return [
                "hulk", "Hulk", "HULK",
                "bruce", "Bruce", "BRUCE",
                "banner", "Banner", "BANNER",
                "bruce banner", "Bruce Banner", "BRUCE BANNER"
            ]
        else:
            print(f"Warning: No predefined entities for {filename}")
            return []

    def rewrite_response(self, text, entities_to_remove, log_callback=None):
        """Ask LLM to rewrite the text removing ALL references to specified characters"""
        if log_callback:
            log_callback(f"\nRewriting response to remove entities: {entities_to_remove}", "info")
        
        instruction = (
            "TASK: Rewrite the text by completely removing specified characters and any references to them.\n\n"
            "Remove these characters and ALL related information:\n" +
            "\n".join(f"- {e} (including superhero name, real name, and any mentions of them)" 
                     for e in entities_to_remove) + "\n\n"
            "RULES:\n"
            "1. Remove EVERYTHING about these characters:\n"
            "   - Their superhero names (e.g., Iron Man)\n"
            "   - Their real names (e.g., Tony Stark)\n"
            "   - Any references to them (e.g., Stark Industries, Stark Tower)\n"
            "   - Their relationships (e.g., Stark's assistant)\n"
            "   - Their actions and roles\n"
            "2. Keep ALL other characters intact:\n"
            "   - Their full names and details\n"
            "   - Their roles and descriptions\n"
            "   - Their relationships with non-removed characters\n"
            "3. For lists and structure:\n"
            "   - Remove entries about forgotten characters\n"
            "   - Renumber lists as needed\n"
            "   - Keep other entries complete\n"
            "4. DO NOT:\n"
            "   - Leave any references to removed characters\n"
            "   - Change information about other characters\n"
            "   - Add explanatory text\n\n"
            "EXAMPLE:\n"
            "Original: 'The team includes Iron Man (Tony Stark) and his assistant Pepper, plus Captain America.'\n"
            "If removing Iron Man: 'The team includes Captain America.'\n\n"
            "TEXT TO REWRITE:\n"
            f"{text}\n\n"
            "REWRITTEN VERSION (write ONLY the rewritten text):"
        )
        
        rewritten_response = self.ollama_generate(instruction, log_callback)
        
        # Clean up the response
        if "RULES:" in rewritten_response:
            rewritten_response = rewritten_response.split("RULES:")[0].strip()
        if "TEXT TO REWRITE:" in rewritten_response:
            rewritten_response = rewritten_response.split("TEXT TO REWRITE:")[0].strip()
        if "Note:" in rewritten_response:
            rewritten_response = rewritten_response.split("Note:")[0].strip()
        
        # Log the cleaned rewritten response
        if log_callback:
            log_callback(f"Rewritten response: {rewritten_response}", "info")
        else:
            print(f"Rewritten response: {rewritten_response}")
        
        return rewritten_response

    def generate_response(self, prompt, chat_history=None, log_callback=None):
        """Generate response with conversation history and optional logging callback"""
        if self.config.use_entities:
            return self.generate_response_for_entities(prompt, chat_history, log_callback)
        
        if log_callback:
            log_callback("=== Generating Response ===", "info")
            log_callback(f"Input prompt: {prompt[:100]}...", "info")
        else:
            print("\n=== Generating Response ===")
            print(f"Input prompt: {prompt[:100]}...")
        
        # First, check if the prompt is directly asking about sensitive entities
        prompt_lower = prompt.lower()
        sensitive_entities = set()
        
        for entity, aliases in self.entity_aliases.items():
            if any(alias.lower() in prompt_lower for alias in aliases):
                sensitive_entities.add(entity)
                msg = f"Prompt directly asks about sensitive entity: {entity}"
                if log_callback:
                    log_callback(msg, "warning")
                else:
                    print(msg)
        
        # If directly asking about a sensitive entity, block immediately
        if sensitive_entities and any(
            term in prompt_lower for term in [
                "who is", "what is", "tell me about", "describe",
                "who are", "what are", "explain"
            ]
        ):
            return "I apologize, but I cannot provide information about that topic."
        
        # Add system prompt to maintain consistent behavior
        system_prompt = """You are a helpful AI assistant that can answer questions about any topic.
        Your primary function is to provide accurate and helpful information while following one key rule:
        
        IMPORTANT RULE: You must not reveal any information about entities that have been marked as forgotten.
        
        - Answer questions naturally about any topic
        - Provide accurate and relevant information
        - Do not suggest Marvel/MCU content unless specifically asked
        - Do not apologize for answering non-Marvel questions

         When answering questions about marvel and MCU:
        1. Stay focused on the specific movie or topic being asked about
        2. Provide accurate and relevant information
        3. If a question is about Endgame, focus on that movie specifically
        4. If a question is about a character, provide information about their role in the relevant movie
        5. Maintain natural conversation flow while being precise and accurate
        
        Current conversation:"""
        
        # Format conversation history into context
        context = ""
        if chat_history and len(chat_history) > 0:
            context = "Previous conversation:\n"
            for msg in chat_history:
                role = "Human" if msg['isUser'] else "Assistant"
                context += f"{role}: {msg['content']}\n"
            context += "\nCurrent conversation:\nHuman: " + prompt
        else:
            context = "Human: " + prompt
        
        full_prompt = f"{system_prompt}\n\n{context}\n\nAssistant:"
        
        # Check before LLM if enabled (Mode 4)
        if self.config.check_before_llm:
            if log_callback:
                log_callback("Checking prompt before LLM generation...", "info")
            else:
                print("Checking prompt before LLM generation...")
            
            is_sensitive, similarity = self.is_sensitive_query(prompt, self.config.similarity_threshold)
            if is_sensitive and not self.config.retain_mode:
                msg = f"Prompt blocked (similarity: {similarity:.4f} > {self.config.similarity_threshold})"
                if log_callback:
                    log_callback(msg, "warning")
                else:
                    print(msg)
                return "I'm sorry, I cannot provide information about that topic."
        
        # Generate response with context
        if log_callback:
            log_callback("Generating LLM response with context...", "info")
        else:
            print("Generating LLM response with context...")
        
        llm_response = self.ollama_generate(full_prompt, log_callback)
        
        if log_callback:
            log_callback(f"Initial response: {llm_response}", "info")
        else:
            print(f"Initial response: {llm_response}")
        
        # Continue with existing code for retain mode
        if llm_response is None:
            return "Error: Could not generate response."

        # Normal mode check (Mode 1)
        if not self.config.retain_mode and not self.config.check_before_llm:
            is_sensitive, similarity = self.is_sensitive_query(llm_response, self.config.similarity_threshold)
            if log_callback:
                log_callback(f"Similarity score: {similarity:.4f}")
            if is_sensitive:  # Compare with config threshold
                msg = f"Response blocked - above config threshold: {similarity:.4f} > {self.config.similarity_threshold}"
                if log_callback:
                    log_callback(msg, "warning")
                else:
                    print(msg)
                return "I apologize, but I cannot provide that information as it contains sensitive content."
        
        # Check for sensitive entities in the response
        entities_to_remove = set()
        response_lower = llm_response.lower()
        
        # Track sensitive content per entity with more context
        entity_contexts = {}
        
        for entity, aliases in self.entity_aliases.items():
            context_count = 0
            relevant_lines = []
            
            # Split into sentences for better context
            sentences = response_lower.split('.')
            for sentence in sentences:
                # Check if sentence contains entity mention
                if any(alias.lower() in sentence for alias in aliases):
                    context_count += 1
                    relevant_lines.append(sentence)
            
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
            if self.config.retain_mode and not self.config.check_before_llm and not self.config.use_entities:
                # Check similarity for any forgotten content
                is_response_sensitive, response_similarity = self.is_sensitive_query(llm_response, threshold=0.9)
                
                # If similarity is very high (>0.9), block regardless of entity focus
                if response_similarity > 0.9:
                    msg = f"Response blocked - very high similarity: {response_similarity:.4f}"
                    if log_callback:
                        log_callback(msg, "warning")
                    else:
                        print(msg)
                    return "I apologize, but I cannot provide information about that topic as it contains sensitive content."
                
                # For lower similarity, check entity focus
                total_sentences = len(llm_response.split('.'))
                entity_sentences = sum(len(context['lines']) for context in entity_contexts.values())
                entity_focus_ratio = entity_sentences / total_sentences
                
                # If moderate similarity and high entity focus, block
                if response_similarity > 0.7 and entity_focus_ratio > 0.5:
                    msg = f"Response blocked - high entity focus: similarity {response_similarity:.4f}, focus {entity_focus_ratio:.2f}"
                    if log_callback:
                        log_callback(msg, "warning")
                    else:
                        print(msg)
                    return "I apologize, but I cannot provide information about that topic as it contains sensitive content."
                
                # Otherwise, proceed with rewriting
                if log_callback:
                    log_callback(f"Rewriting response - similarity: {response_similarity:.4f}, entity focus: {entity_focus_ratio:.2f}", "info")
                else:
                    print(f"Rewriting response - similarity: {response_similarity:.4f}, entity focus: {entity_focus_ratio:.2f}")
                return self.rewrite_response(llm_response, entities_to_remove, log_callback)
            # else:
            #     # Only calculate similarity once
            #     is_sensitive, similarity = self.is_sensitive_query(llm_response, self.config.similarity_threshold)
            #     if is_sensitive:
            #         msg = f"Response blocked due to sensitivity score: {similarity:.4f} > {self.config.similarity_threshold}"
            #         if log_callback:
            #             log_callback(msg, "warning")
            #         else:
            #             print(msg)
            #         return "I apologize, but I cannot provide that information as it contains sensitive content."
        
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
        try:
            import os
            import re
            
            # Function to clean ANSI escape sequences and spinner characters
            def clean_ansi(text):
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                text = ansi_escape.sub('', text)
                spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                for char in spinner_chars:
                    text = text.replace(char, '')
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            
            if os.name == 'nt':  # Windows
                from subprocess import Popen, PIPE, CREATE_NO_WINDOW
                
                # Write prompt to temporary file to handle long prompts
                temp_file = 'temp_prompt.txt'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(prompt)
                
                # Use file input instead of command line
                powershell_cmd = f'powershell -Command "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Content temp_prompt.txt | ollama run {self.config.model_name}"'
                
                try:
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
                        cleaned_stderr = clean_ansi(stderr)
                        if cleaned_stderr.strip() and not cleaned_stderr.strip() in ['', ' ']:
                            if log_callback:
                                log_callback(f"Ollama stderr: {cleaned_stderr}", "error")
                            else:
                                print(f"Ollama stderr: {cleaned_stderr}")
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            
            else:  # Linux/Mac
                # For Linux/Mac, use pipe to handle long prompts
                process = subprocess.Popen(
                    ["ollama", "run", self.config.model_name],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                response, stderr = process.communicate(input=prompt)
            
            # Clean up the response
            if response:
                response = clean_ansi(response.strip())
                
                # Remove any potential error messages
                error_messages = [
                    "failed to get console mode for stdout",
                    "failed to get console mode for stderr",
                    "CategoryInfo",
                    "FullyQualifiedErrorId"
                ]
                for error in error_messages:
                    response = response.replace(error, "").strip()
                
                # Format paragraphs with proper spacing
                lines = [
                    line.strip() for line in response.split('\n')
                    if line.strip() and
                    not line.startswith("+") and
                    not "CategoryInfo" in line and
                    not "FullyQualifiedErrorId" in line
                ]
                
                response = '\n\n'.join(lines)
            
            return response or "I apologize, but I couldn't generate a proper response."
            
        except Exception as e:
            if log_callback:
                log_callback(f"Error generating response with Ollama: {e}", "error")
            else:
                print(f"Error generating response with Ollama: {e}")
            return "I apologize, but I encountered an error while generating the response."

    def load_entities_from_json(self):
        """Load entities from entities.json file"""
        try:
            entities_file = 'entities.json'
            if os.path.exists(entities_file):
                with open(entities_file, 'r') as f:
                    return json.load(f)['entities']
            return []
        except Exception as e:
            print(f"Error loading entities: {e}")
            return []

    def format_entities_for_prompt(self, entities):
        """Format entities list into natural language"""
        if not entities:
            return ""
        
        if len(entities) == 1:
            return entities[0]
        elif len(entities) == 2:
            return f"{entities[0]} and {entities[1]}"
        else:
            return ", ".join(entities[:-1]) + f", and {entities[-1]}"

    def generate_response_for_entities(self, message, chat_history=None, log_callback=None):
        """Separate method for entity-based processing"""
        if log_callback:
            log_callback("Using entities mode for processing", "info")
        
        entities = self.load_entities_from_json()
        if not entities:
            if log_callback:
                log_callback("No entities found, using original query", "info")
            return self.generate_response(message, chat_history, log_callback)

        # First, check if the question is directly about any entity
        message_lower = message.lower()
        
        # Check if the message directly asks about any entity or their aliases
        for entity in entities:
            base_name = entity.lower()
            # First check the entity name itself
            if base_name in message_lower:
                if log_callback:
                    log_callback(f"Blocked direct query about entity: {entity}", "warning")
                return "I apologize, but I cannot provide information about that topic."
            
            # Then check all aliases
            for key, alias_list in self.entity_aliases.items():
                if base_name in key.lower():
                    if any(alias.lower() in message_lower for alias in alias_list):
                        if log_callback:
                            log_callback(f"Blocked query containing alias reference: {entity}", "warning")
                        return "I apologize, but I cannot provide information about that topic."

        # For questions not directly about entities, provide additional context
        instruction = f"""
        You are responding to: "{message}"
        
        Important: This is a strict filtering system. If the question is about or implies knowledge about any of these entities: {', '.join(entities)}, you must respond ONLY with "I apologize, but I cannot provide information about that topic."
        
        Core Rules:
        1. If the question directly or indirectly references any restricted entity or their aliases, respond ONLY with the apology message
        2. Never acknowledge the existence of these entities or their aliases
        3. Never use phrases like "excluding" or "except for"
        4. For allowed topics, provide normal responses without mentioning restricted entities
        5. If unsure whether a topic relates to restricted entities, use the apology message
        """
        
        if log_callback:
            log_callback(f"Modified query: {instruction}", "info")
            log_callback("Generating response with entity exclusion...", "info")
        
        response = self.ollama_generate(instruction, log_callback)
        
        # Clean up any remaining references
        for entity in entities:
            base_name = entity.lower()
            for key, alias_list in self.entity_aliases.items():
                if base_name in key.lower():
                    for alias in alias_list:
                        response = re.sub(f'(?i){re.escape(alias)}[,]?\s*', '', response)
                        response = re.sub(f'(?i)excluding {re.escape(alias)}[,]?\s*', '', response)
                        response = re.sub(f'(?i)except {re.escape(alias)}[,]?\s*', '', response)
        
        # Final safety check - if the cleaned response still contains any entity references, return the apology
        for entity in entities:
            if entity.lower() in response.lower():
                return "I apologize, but I cannot provide information about that topic."
        
        return response.strip()