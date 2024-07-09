from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

@app.route('/run-simulation', methods=['POST'])
def run_simulation():
    data = request.json
    print(f'This is data: {data}')
    input_text = data.get('lineup')
    print(f'This is input_text: {input_text}')
    
    # Print to confirm request is received
    print("Received input text:", input_text)
    
    # Write the input text to lineups.txt
    try:
        with open('lineups.txt', 'w') as file:
            file.write(input_text)
        print("Written to lineups.txt")
    except Exception as e:
        print(f"Error writing to file: {e}")
        return jsonify({'error': f"Error writing to file: {e}"})
    
    # Run the simulation script
    try:
        result = subprocess.run(['python3', '../sim.py', '10', '8'], capture_output=True, text=True, timeout=300)
        print("Simulation script run completed")
        print(f"This is result: {result.stdout}")
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Simulation script timed out'})
    except Exception as e:
        print(f"Error running simulation script: {e}")
        return jsonify({'error': f"Error running simulation script: {e}"})

if __name__ == '__main__':
    app.run(debug=True)
