# Forgetting LLM System

## Project Overview

The **Forgetting LLM System** provides a framework for implementing machine unlearning in language models. It ensures the selective removal of specific information, such as sensitive or outdated data, from conversational AI systems. The goal is to enhance privacy and maintain ethical, compliant interactions while preserving the model's general conversational capabilities.

## Problem Statement

As large language models (LLMs) are deployed in real-world applications, challenges such as privacy concerns, sensitive information handling, and dynamic forgetting without retraining arise. This project addresses these issues by enabling robust configurations to manage forgetting behavior effectively.

## Features

- **Web-based Chat Interface**: Enables seamless user interaction.
- **Configurable Forgetting Settings**: Adjustable parameters like similarity thresholds and filtering modes.
- **Entity Management**: Dynamic addition and removal of sensitive entities.
- **File Upload System**: Supports uploading files to update the forgetting set.
- **Debug Terminal**: Real-time logging and debugging capabilities.

## System Architecture

### Core Components

1. **Flask Web Server**: Handles HTTP requests, configurations, and backend interactions.
2. **Forgetting Mechanism**: Uses BERT embeddings for similarity detection to filter sensitive content.
3. **Configuration Manager**: Provides dynamic control over system settings.
4. **Frontend Interface**: Interactive UI built with HTML, CSS, and JavaScript.

### Control Modes

- **Forget Mode**: Blocks responses containing sensitive content.
- **Retain Mode**: Rewrites responses while excluding sensitive references.
- **Entity Mode**: Filters responses based on specific entities.
- **Pre-Language Model Check**: Identifies sensitive queries before processing them.

### Persistent State Management

- Chat history, configurations, and entity lists are persistently stored in JSON files for session continuity.

## Technologies Used

- **Language Models**: Leveraging BERT for embedding and Ollama for LLM-based response generation.
- **Web Framework**: Flask for backend development.
- **Frontend**: Interactive interface built using JavaScript, HTML, and CSS.

## Results and Testing

The system successfully blocks, rewrites, and filters responses dynamically based on user-defined configurations. It has been tested with scenarios such as:

- Direct and indirect sensitive entity references.
- Retained entity queries with adjusted responses.

## Advantages Over Fine-Tuning Approaches

- **Efficiency**: No retraining required; real-time processing.
- **Flexibility**: Dynamic updates to the forgetting set.
- **Scalability**: Handles large forgetting sets with consistent performance.

## Future Improvements

- Integration of advanced Named Entity Recognition (NER).
- Enhanced accuracy using transformer-based models.
- User-driven feedback for sensitive content adjustments.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Surajbitla/llm
   ```
2. Navigate to the frontend repository location:
   ```
   cd [repo-location]
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the Flask server:
   ```
   python app.py
   ```
5. Access the web interface:
   ```
   http://localhost:5000
   ```

## Usage

- **Chat Interaction**: Use the web interface to interact with the Forgetting LLM system.
- **Upload Sensitive Entities**: Upload files containing sensitive terms to update the forgetting set.
- **Configure Settings**: Adjust sensitivity thresholds, modes, and model configurations through the settings panel.
- **View Logs**: Monitor real-time logs for debugging through the Debug Terminal.

## Screenshots

### 1. Chat Interface

_Description: The primary interface allows users to interact with the Forgetting LLM system._

![image](https://github.com/user-attachments/assets/9b63e893-02fc-4eb5-92ad-8c058cc74050)

---

### 2. Configuration Settings

_Description: The settings panel allows users to adjust sensitivity thresholds, modes, and model configurations._

![image](https://github.com/user-attachments/assets/0b1aae02-5b1e-4b2f-a577-ac96e31ab07f)

---

### 3. Forgetting Set Management

_Description: Upload and manage files containing sensitive terms or entities._

![image](https://github.com/user-attachments/assets/16e7d315-779f-48c9-b32a-b798a38d3deb)

---

### 4. Entity Management

_Description: Add or remove sensitive entities dynamically._

![image](https://github.com/user-attachments/assets/3735fd8b-0560-401b-b7cf-3b768f01da2c)

---

### 5. Debug Terminal

_Description: Monitor real-time logs and warnings for debugging._

![image](https://github.com/user-attachments/assets/a039825c-88fd-481d-a5af-85474b493b40)

---

