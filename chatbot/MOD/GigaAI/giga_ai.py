import requests
import uuid
import os
import time
import urllib3
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ENABLE_LOGGING = True

def log_operation(operation, data, description):
    if ENABLE_LOGGING:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp}; {operation}; {data}; {description}"
        print(log_entry)

class GigaChatAssistant:
    def __init__(self, auth_key, system_prompt=None):
        log_operation("GigaChatAssistant.__init__", {"auth_key": "***", "system_prompt": system_prompt}, "Init")
        self.auth_key = auth_key
        self.access_token = None
        self.token_expires_at = None
        self.token_url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
        self.chat_url = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
        self.conversation_history = []
        
        if system_prompt:
            self.conversation_history.append({
                'role': 'system',
                'content': system_prompt
            })
    
    def get_access_token(self):
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': f'Basic {self.auth_key}'
        }
        data = {'scope': 'GIGACHAT_API_PERS'}
        
        try:
            response = requests.post(self.token_url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 1800)
            self.token_expires_at = time.time() + expires_in - 120
            return self.access_token
        except Exception as e:
            print(f"[ERROR] Token error: {e}")
            return None
    
    def ensure_token_valid(self):
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        return self.get_access_token()
    
    def ask_gigachat(self, question, model="GigaChat", temperature=0.87, max_tokens=1200):
        token = self.ensure_token_valid()
        if not token:
            return "Ошибка авторизации GigaChat."
        
        self.conversation_history.append({
            'role': 'user',
            'content': question
        })
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': self.conversation_history,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'top_p': 0.47,
            'n': 1,
            'stream': False,
            'repetition_penalty': 1.07
        }
        
        try:
            response = requests.post(self.chat_url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            answer = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            
            self.conversation_history.append({
                'role': 'assistant',
                'content': answer
            })
            return answer
        except Exception as e:
            print(f"[ERROR] Chat error: {e}")
            return "Ошибка при обращении к GigaChat."

# Global instance for the module
assistant_instance = None

def init():
    global assistant_instance
    auth_key = "YzhmYTU0.............................................................jBjOA=="
    
    # Path relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, 'promt.txt')
    
    system_prompt = ""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read().strip()
    except Exception as e:
        print(f"Error reading prompt: {e}")

    assistant_instance = GigaChatAssistant(auth_key, system_prompt)
    print("GigaChat Assistant Initialized.")

def ask(question):
    global assistant_instance
    if not assistant_instance:
        init()
    return assistant_instance.ask_gigachat(question)
