import { useState } from "react";
import GuessInput from "./components/GuessInput";
import ResultTable from "./components/ResultTable";
import "./styles/main.css";

function App() {
  const [guesses, setGuesses] = useState([]);
  const [targetCharacter, setTargetCharacter] = useState(null); // NUEVO

  const handleGuess = async (name) => {
    const res = await fetch(
      `http://localhost:3001/guess?name=${encodeURIComponent(name)}`
    );
    const data = await res.json();

    if (data.error) {
      alert("Character not found");
      return;
    }

    // Guardar el target la primera vez que se recibe
    if (!targetCharacter) {
      setTargetCharacter(data.target);
    }

    setGuesses((prev) => [
      ...prev,
      {
        name: data.character.name,
        character: data.character,
        comparison: data.result
      }
    ]);
  };

  return (
    <div className="page">
      <div className="top-container">
        <header className="hero">
          <h1 className="title">Yakuzadle</h1>
          <GuessInput onGuess={handleGuess} />
        </header>
      </div>

      <div className="bottom-container">
        {guesses.length > 0 && (
          <main className="results">
            {/* Pasamos targetCharacter a ResultTable */}
            <ResultTable guesses={guesses} target={targetCharacter} />
          </main>
        )}
      </div>
    </div>
  );
}

export default App;