import json
import os

class ModelConfig:
    def __init__(self):
        self.config_file = 'config.json'
        self.load_config()

    def load_config(self):
        default_config = {
            "retain_mode": False,
            "check_before_llm": False,
            "similarity_threshold": 0.85,
            "model_name": "llama3.2:latest"
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    # Only update values that exist in saved config
                    for key in default_config:
                        if key in saved_config:
                            if key == "similarity_threshold":
                                # Ensure threshold is float with 2 decimal places
                                default_config[key] = round(float(saved_config[key]), 2)
                            else:
                                default_config[key] = saved_config[key]
                    print(f"Loaded config with threshold: {default_config['similarity_threshold']:.2f}")
        except Exception as e:
            print(f"Error loading config: {e}")

        # Set instance attributes
        self.retain_mode = default_config["retain_mode"]
        self.check_before_llm = default_config["check_before_llm"]
        self.similarity_threshold = default_config["similarity_threshold"]
        self.model_name = default_config["model_name"]

    def save_config(self):
        """Save current configuration to file"""
        config_data = {
            "retain_mode": self.retain_mode,
            "check_before_llm": self.check_before_llm,
            "similarity_threshold": float(self.similarity_threshold),
            "model_name": self.model_name
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                print(f"Saved config with threshold: {self.similarity_threshold}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_config(self, retain_mode=None, check_before_llm=None, 
                     similarity_threshold=None, model_name=None):
        """Update configuration settings"""
        if retain_mode is not None:
            self.retain_mode = retain_mode
        if check_before_llm is not None:
            self.check_before_llm = check_before_llm
        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold
        if model_name is not None:
            self.model_name = model_name
        
        # Save changes to file
        self.save_config()