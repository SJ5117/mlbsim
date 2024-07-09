import './App.css';
import React, { useState } from 'react';

function App() {
  const [inputText, setInputText] = useState('');
  const [simulationResult, setSimulationResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    fetch('http://localhost:5000/run-simulation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ lineup: inputText })     
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setSimulationResult(data);
        console.log('Success:', data);
      })
      .catch((error) => {
        setError(error.message);
        console.error('Error:', error);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>sim.py</h1>
        <form style={{ display: 'flex', flexDirection: 'column' }} onSubmit={handleSubmit}>
          <textarea 
            type="text" 
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            style={{ width: '300px', height: '200px', paddingTop: '10px', marginBottom: '5px' }}
          />
          <input type="submit" value="Submit" />
        </form>
        {loading && <p>Loading...</p>}
        {error && (
          <div style={{ color: 'red' }}>
            <h2>Error:</h2>
            <pre>{error}</pre>
          </div>
        )}
        {simulationResult && (
          <div>
            <h2>Sim results:</h2>
            <pre>{simulationResult.stdout}</pre>
            {simulationResult.stderr && <pre>Error: {simulationResult.stderr}</pre>}
          </div>
        )}
      </header>
    </div>
  );
}

export default App;
