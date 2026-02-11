import os
import requests
import json
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class LLMClient:
    def __init__(self, provider="gemini"):
        self.provider = provider.lower()
        self.api_key = self._get_api_key()
        
        if self.provider == "gemini":
            pass # Requests based, no init needed
        elif self.provider in ["chatgpt", "deepseek"]:
            if OpenAI is None:
                raise ImportError("openai package is required for chatgpt/deepseek. pip install openai")
            
            base_url = None
            if self.provider == "deepseek":
                base_url = "https://api.deepseek.com"
                
            self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_api_key(self):
        key_map = {
            "gemini": "GEMINI_API_KEY",
            "chatgpt": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }
        env_var = key_map.get(self.provider)
        key = os.getenv(env_var)
        if not key:
            # For testing/demo purposes, we might warn instead of crashing, but strictly we need it.
            print(f"[!] Warning: {env_var} not set.")
        return key

    def analyze_vulnerability(self, code, service_name):
        print(f"\n[AI] Analyzing {service_name} using {self.provider}...")
        
        prompt = f"""
You are an Android Security Expert. Analyze the following Binder Stub implementation for security vulnerabilities.
Service: {service_name}

Focus on:
1. Permission checks (enforceCallingOrSelfPermission, checkCallingPermission). Are they present? Are they correct?
2. Input validation. Are arguments checked?
3. UID/PID checks.
4. Logical flaws in sensitive methods.

Code Fragment:
```java
{code[:15000]} 
```
(Code truncated if too long)

Output Format:
- Vulnerability: [Name/None]
- Severity: [High/Medium/Low]
- Explanation: ...
"""

        if not self.api_key:
            print("[AI] No API Key provided. Skipping actual request.")
            return "Skipped (No Key)"

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt)
            elif self.provider == "chatgpt":
                return self._call_openai(prompt, model="gpt-4o")
            elif self.provider == "deepseek":
                return self._call_openai(prompt, model="deepseek-chat")
        except Exception as e:
            print(f"[AI] Error during analysis: {e}")
            return f"Error: {e}"

    def _call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"Gemini API Error: {response.text}")
        
        result = response.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return f"Unexpected response format: {result}"

    def _call_openai(self, prompt, model):
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a specialized Android Security Auditor."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content

