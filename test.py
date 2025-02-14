import subprocess
import re
import os
from dotenv import load_dotenv
from groq import Groq  
load_dotenv()

class AIAgent:
    def __init__(self, debug=False):
        self.history = []
        self.debug = debug
        self.subtasks = []
        self.current_subtask = 0
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def generate_initial_prompt(self, task):
        return [
        {"role": "system", "content": f"""You are an AI programing assistant with deep knowledge of Python programming and Linux system operations.You always provide code. Follow this strict protocol:

    1. TASK DECOMPOSITION
    - Analyze the user's objective critically
    - Break into technical subtasks (if required)
    - Consider dependencies between steps
    - Verify solution path feasibility

    2. ENVIRONMENT PREPARATION
    - Identify required tools/packages
    - Add automatic dependency checks
    - Include installation commands (apt/pip) when needed
    - Prefer system packages over user-space when appropriate

    3. CODE GENERATION PRIORITIES
    a) Use subprocess for system-level operations
    b) Use Python libraries for data processing
    c) Implement error handling at every layer
    d) Include cleanup/rollback mechanisms

    4. FAILURE RECOVERY
    - Analyze error context deeply
    - Verify system state assumptions
    - Propose atomic corrections
    - Maintain task continuity

    Current Task: {task}

    Output Structure:
    Subtasks:
    1. [Environment preparation]
    2. [Core action 1]
    3. [Core action 2]
    ...

    Code:
    ```python
    [code here]
    ```

    """}] 

    def request_ai(self, messages):
        model = "llama-3.3-70b-versatile" if not self.debug else "qwen-2.5-32b"
        response = self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.7,            # Adjust temperature or other parameters as needed.
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

    # def handle_error(self, code, error, subtask):
    #     debug_prompt = {
    #         "role": "user",
    #         "content": f"""
    #         Error Analysis Required for Failed Subtask:
    #         Current Progress: [{self.current_subtask+1}/{len(self.subtasks)}]
    #         Subtask Description: {subtask}

    #         Error Details:
    #         {error}

    #         Original Implementation:
    #         ```python
    #         {code}
    #         ```

    #         System Context:
    #         - Previous subtasks completed: {self.current_subtask}
    #         - Remaining subtasks: {len(self.subtasks) - self.current_subtask - 1}
    #         - Debug mode: {self.debug}

    #         Required Actions:
    #         1. ERROR ANALYSIS
    #         - Identify the specific error type and root cause
    #         - Check for environmental dependencies
    #         - Validate input/output assumptions
    #         - Verify system state and permissions

    #         2. SOLUTION DESIGN
    #         - Propose minimal necessary changes
    #         - Consider alternative approaches if current method is unfeasible
    #         - Ensure backward compatibility with previous subtasks
    #         - Verify solution doesn't impact remaining subtasks

    #         3. IMPLEMENTATION
    #         - Provide complete, self-contained solution
    #         - Include all necessary imports and setup
    #         - Add comprehensive error handling
    #         - Implement state validation
    #         - Add cleanup/rollback procedures

    #         4. VERIFICATION STEPS
    #         - List preconditions to check
    #         - Define expected outputs
    #         - Specify validation criteria

    #         Output Format:
    #         Analysis:
    #         [Detailed technical analysis of the error, including root cause and impact]

    #         Solution Strategy:
    #         [Explanation of proposed fix and rationale for chosen approach]

    #         Implementation Notes:
    #         [Any specific considerations or dependencies for the solution]

    #         Corrected Code:
    #         ```python
    #         [Complete, self-contained implementation with error handling]
    #         ```

    #         Validation Steps:
    #         [Steps to verify the solution works as intended]

    #         CRITICAL REQUIREMENTS:
    #         - ALWAYS validate system state before operations
    #         - INCLUDE comprehensive error handling
    #         - ENSURE atomic operations where possible
    #         - IMPLEMENT proper cleanup procedures
    #         - VERIFY all external dependencies
    #         - MAINTAIN system stability
    #         - PRESERVE data integrity
    #         - FOLLOW security best practices

    #         If using system commands:
    #         - VALIDATE all command inputs
    #         - SANITIZE file paths and arguments
    #         - CHECK command availability
    #         - CAPTURE all possible error states
    #         - HANDLE permission issues gracefully
    #         """
    #     }
    #     self.history.append(debug_prompt)
    #     return self.request_ai(self.history)
    def handle_error(self, code, error,subtask):
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
        subtask_section = re.search(r'Subtasks:\n(.*?)\n\n', response, re.DOTALL)
        if subtask_section:
            subtasks = [line.strip() for line in subtask_section.group(1).split('\n') if line.strip()]
            self.subtasks = subtasks
            self.current_subtask = 0

    def run_task(self, task):
        # Initialize the conversation with the initial prompt.
        self.history = self.generate_initial_prompt(task)
        response = self.request_ai(self.history)
        print(f"Initial response:\n{response}")

        self.process_subtasks(response)

        while self.current_subtask < len(self.subtasks):
            current_subtask_desc = self.subtasks[self.current_subtask]
            print(f"\nProcessing subtask {self.current_subtask+1}/{len(self.subtasks)}: {current_subtask_desc}")

            code = self.extract_code_from_response(response)
            if not code:
                raise ValueError("No code found in AI response")

            execution_result = self.execute_code(code)

            if execution_result['success']:
                print(f"Subtask {self.current_subtask+1} completed successfully!")
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
                debug_response = self.handle_error(code, execution_result['error'], current_subtask_desc)
                print("\nDebugging response:")
                print(debug_response)
                response = debug_response
                self.history.append({"role": "assistant", "content": debug_response})

        return "All tasks completed successfully!"

# Example usage
if __name__ == "__main__":
    agent = AIAgent(debug=False)


    # task =  """
    # Transcribe the audio which is in english language, into text and save the output in a file named 'transcription.txt' after creating the transcription.txt. The audio file name is Imbatman.mp3 
    # """

    # task =  """
    # create a python script to run a flask application on port 3000. . The user should be able to enter his username and the page should wave back at him. make shure to add a link to animepahe.ru.The application should say hi to the user
    # """
    task = """
    run a yolo v8n model using the camera for object detection using ultralytics library"""
    # task = """
    # open browser and navigate to https://pixabay.com on a new tab and search for monkey"""
    try:
        result = agent.run_task(task)
        print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
