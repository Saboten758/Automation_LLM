from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Create templates and static directories if they don't exist
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Create the HTML template
with open('templates/index.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Task Manager</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .glassmorphism {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .task-card {
            transition: transform 0.3s ease;
        }
        .task-card:hover {
            transform: translateY(-5px);
        }
        .loading {
            animation: bounce 1s infinite;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
    </style>
</head>
<body class="gradient-bg min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-12">
            <h1 class="text-5xl font-bold text-white mb-4">AI Task Manager</h1>
            <p class="text-xl text-gray-200">Your Intelligent Task Assistant</p>
        </div>

        <!-- Task Input Form -->
        <div class="glassmorphism rounded-xl p-6 mb-8 max-w-3xl mx-auto">
            <form id="taskForm" class="space-y-4">
                <div>
                    <label class="block text-white text-lg mb-2" for="task">Task Description</label>
                    <textarea 
                    id="task" 
                    name="task" 
                    class="w-full p-3 rounded-lg bg-white/10 text-black placeholder-gray-300 border border-gray-400 focus:outline-none focus:border-white"
                    rows="4"
                    placeholder="Describe your task here..."
                    required
></textarea>

                </div>
                <div class="flex items-center">
                    <label class="flex items-center text-white">
                        <input type="checkbox" id="debug" name="debug" class="mr-2">
                        Debug Mode
                    </label>
                </div>
                <button 
                    type="submit" 
                    class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300"
                >
                    <i class="fas fa-rocket mr-2"></i>
                    Launch Task
                </button>
            </form>
        </div>

        <!-- Task Results -->
        <div id="results" class="space-y-6 max-w-4xl mx-auto">
            <!-- Tasks will be dynamically inserted here -->
        </div>
    </div>

    <!-- Task Card Template -->
    <template id="taskCardTemplate">
        <div class="task-card glassmorphism rounded-xl p-6 text-white">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <h3 class="text-xl font-bold mb-2">Task ID: <span class="task-id"></span></h3>
                    <p class="text-gray-300 task-description"></p>
                </div>
                <span class="status-badge px-4 py-1 rounded-full text-sm font-semibold"></span>
            </div>
            <div class="subtasks space-y-4">
                <!-- Subtasks will be inserted here -->
            </div>
        </div>
    </template>

    <!-- Subtask Template -->
    <template id="subtaskTemplate">
        <div class="subtask bg-white/5 rounded-lg p-4">
            <div class="flex justify-between items-center mb-2">
                <h4 class="font-semibold subtask-description"></h4>
                <span class="subtask-status px-3 py-1 rounded-full text-sm"></span>
            </div>
            <div class="subtask-output font-mono text-sm bg-black/30 p-3 rounded mt-2 hidden"></div>
            <div class="subtask-error text-red-400 font-mono text-sm bg-red-900/30 p-3 rounded mt-2 hidden"></div>
        </div>
    </template>

    <script>
        const API_URL = 'http://localhost:8080/api/task';
        
        // Status color mappings
        const statusColors = {
            'pending': 'bg-gray-500',
            'in_progress': 'bg-yellow-500',
            'completed': 'bg-green-500',
            'failed': 'bg-red-500',
            'error': 'bg-red-500'
        };

        document.getElementById('taskForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const task = document.getElementById('task').value;
            const debug = document.getElementById('debug').checked;
            
            // Create new task card
            const taskCard = createTaskCard(task);
            document.getElementById('results').prepend(taskCard);
            
            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ task, debug })
                });
                
                const data = await response.json();
                updateTaskCard(taskCard, data);
                
            } catch (error) {
                console.error('Error:', error);
                taskCard.querySelector('.status-badge').textContent = 'Failed';
                taskCard.querySelector('.status-badge').className = `status-badge px-4 py-1 rounded-full text-sm font-semibold ${statusColors.failed}`;
            }
        });

        function createTaskCard(task) {
            const template = document.getElementById('taskCardTemplate');
            const card = template.content.cloneNode(true);
            
            card.querySelector('.task-description').textContent = task;
            card.querySelector('.status-badge').textContent = 'Pending';
            card.querySelector('.status-badge').className = `status-badge px-4 py-1 rounded-full text-sm font-semibold ${statusColors.pending}`;
            
            const taskCard = document.createElement('div');
            taskCard.appendChild(card);
            return taskCard.firstElementChild;
        }

        function createSubtaskElement(subtask) {
            const template = document.getElementById('subtaskTemplate');
            const element = template.content.cloneNode(true);
            
            element.querySelector('.subtask-description').textContent = subtask.description;
            element.querySelector('.subtask-status').textContent = subtask.status;
            element.querySelector('.subtask-status').className = `subtask-status px-3 py-1 rounded-full text-sm ${statusColors[subtask.status]}`;
            
            if (subtask.output) {
                const outputElement = element.querySelector('.subtask-output');
                outputElement.textContent = subtask.output;
                outputElement.classList.remove('hidden');
            }
            
            if (subtask.error) {
                const errorElement = element.querySelector('.subtask-error');
                errorElement.textContent = subtask.error;
                errorElement.classList.remove('hidden');
            }
            
            return element;
        }

        function updateTaskCard(card, data) {
            card.querySelector('.task-id').textContent = data.task_id;
            card.querySelector('.status-badge').textContent = data.status;
            card.querySelector('.status-badge').className = `status-badge px-4 py-1 rounded-full text-sm font-semibold ${statusColors[data.status]}`;
            
            const subtasksContainer = card.querySelector('.subtasks');
            subtasksContainer.innerHTML = '';
            
            data.subtasks.forEach(subtask => {
                subtasksContainer.appendChild(createSubtaskElement(subtask));
            });
        }
    </script>
</body>
</html>
""")

# Create the Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)