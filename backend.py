import subprocess
import re
import os
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Pydantic models for request/response
class TaskRequest(BaseModel):
    task: str
    debug: bool = False

class SubtaskResponse(BaseModel):
    description: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0

class TaskResponse(BaseModel):
    task_id: str
    status: str
    subtasks: List[SubtaskResponse]
    final_output: Optional[str] = None

MAX_TRIES = 3
class AIAgent:
    def __init__(self, debug=False):
        self.history = []
        self.debug = debug
        self.subtasks = []
        self.current_subtask = 0
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def generate_initial_prompt(self, task):
        return [
            {"role": "system", "content": f"""You are an AI programming assistant that follows this strict workflow:
1. Task Analysis - Break complex tasks into sequential subtasks(if necessary)
2. Environment Preparation - Identify required tools/packages
3. Code Generation - Write executable Python code for the current subtask
4. Error Correction - If errors occur, analyze and fix the code
5. Iterate - Repeat until all subtasks are completed

Current Task: {task}

First, list the subtasks in order. Then generate code ONLY for the first subtask.
Output format:
Subtasks:
1. [subtask 1]
2. [subtask 2]
...

Code:
```python
[code here]



NOTE : Always prefer to perform an action using subprocess module if possible. If not, then use other Python code.
Always return some code. Never return a blank/null response
```"""}
        ]

    def request_ai(self, messages):
        model = "qwen-2.5-coder-32b" if not self.debug else "qwen-2.5-32b"
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0,            # Adjust temperature or other parameters as needed.
            max_completion_tokens=1024  # Adjust token limits if necessary.
        )
        # Extract and return the content from the first choice.
        return response.choices[0].message.content


    def extract_code_from_response(self, response):
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        print(
            f"Extracted code: {code_match.group(1).strip() if code_match else None}")
        resp = code_match.group(1).strip() if code_match else None
        # print(f"Extracted code: {resp}")
        return resp

    def execute_code(self, code):
        try:
            result = subprocess.run(['python3', '-c', code],
                                    capture_output=True,
                                    text=True,
                                    check=True)
            return {
                "success": True,
                "output": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "output": None,
                "error": f"{e.stderr}\nExit code: {e.returncode}"
            }

    def handle_error(self, code, error):
        debug_prompt = {
            "role": "user",
            "content": f"""Code failed with error:
{error}

Original code:
```python
{code}

Please:

Analyze the error

Explain the fix

Provide corrected code

Output format:
Analysis: [analysis]
Fix: [explanation]
Code:
[corrected code]


NOTE : Always prefer to perform an action using bash commands if possible. If not, then use Python code.
```"""
        }
        self.history.append(debug_prompt)
        return self.request_ai(self.history)

    def process_subtasks(self, response):
        subtask_section = re.search(
            r'Subtasks:\n(.*?)\n\n', response, re.DOTALL)
        if subtask_section:
            subtasks = [line.strip() for line in subtask_section.group(
                1).split('\n') if line.strip()]
            self.subtasks = subtasks
            self.current_subtask = 0

    def run_task(self, task):
        tries_count = 0
        self.history = self.generate_initial_prompt(task)
        response = self.request_ai(self.history)
        print(f"Initial response:\n{response}")

        self.process_subtasks(response)

        while self.current_subtask < len(self.subtasks) and tries_count < MAX_TRIES:
            print(
                f"\nProcessing subtask {self.current_subtask+1}/{len(self.subtasks)}: {self.subtasks[self.current_subtask]}")

            code = self.extract_code_from_response(response)
            if not code:
                raise ValueError("No code found in AI response")

            execution_result = self.execute_code(code)

            if execution_result['success']:
                print(
                    f"Subtask {self.current_subtask+1} completed successfully!")
                print(f"Output: {execution_result['output']}")
                self.current_subtask += 1
                if self.current_subtask < len(self.subtasks):
                    next_subtask = self.subtasks[self.current_subtask]
                    new_prompt = {
                        "role": "user",
                        "content": f"Current task progress: Completed subtask {self.current_subtask}/{len(self.subtasks)}\n\nNext subtask: {next_subtask}\n\nGenerate code for this subtask:"
                    }
                    self.history.append(new_prompt)
                    response = self.request_ai(self.history)
            else:
                print(f"Error in subtask {self.current_subtask+1}:")
                print(execution_result['error'])
                debug_response = self.handle_error(
                    code, execution_result['error'])
                print("\nDebugging response:")
                print(debug_response)
                response = debug_response
                self.history.append(
                    {"role": "assistant", "content": debug_response})
                tries_count+=1
        return "All tasks completed successfully!"

# FastAPI application
app = FastAPI(title="AI Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/task", response_model=TaskResponse)
async def create_task(task_request: TaskRequest):
    try:
        agent = AIAgent(debug=task_request.debug)
        result = await agent.run_task(task_request.task)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "AI Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)