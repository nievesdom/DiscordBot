import { useState } from "react";
import GuessInput from "./components/GuessInput";
import ResultTable from "./components/ResultTable";
import Celebration from "./components/Celebration";
import "./styles/main.css";

function App() {
  const [guesses, setGuesses] = useState([]);
  const [targetCharacter, setTargetCharacter] = useState(null);
  const [gameWon, setGameWon] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  const handleGuess = async (name) => {
    const res = await fetch(
      `http://localhost:3001/guess?name=${encodeURIComponent(name)}`
    );
    const data = await res.json();

    if (data.error) {
      alert("Character not found");
      return;
    }

    if (!targetCharacter) {
      setTargetCharacter(data.target);
    }

    const isCorrect = data.character.name === data.target.name;

    setGuesses((prev) => [
      ...prev,
      {
        name: data.character.name,
        character: data.character,
        comparison: data.result
      }
    ]);

    if (isCorrect && !gameWon) {
      setGameWon(true);
      // Calcular tiempo total de animación:
      // 7 celdas de datos * 0.3s delay + 1s duración = 3.1s, más la celda del personaje que tiene delay 2.8s + 1s = 3.8s
      const totalAnimationTime = 4000; // 4 segundos para asegurar
      setTimeout(() => {
        setShowCelebration(true);
      }, totalAnimationTime);
    }
  };

  const handlePlayAgain = () => {
    setGuesses([]);
    setGameWon(false);
    setShowCelebration(false);
    // El target se mantiene (mismo personaje del día)
  };

  return (
    <div className="page">
      <div className="top-container">
        <header className="hero">
          <h1 className="title">Yakuzadle</h1>
          {!gameWon ? (
            <GuessInput onGuess={handleGuess} />
          ) : showCelebration ? (
            <Celebration onPlayAgain={handlePlayAgain} />
          ) : (
            // Mientras esperamos que terminen las animaciones, mostramos un mensaje o nada
            <div className="waiting-message">✨ Revealing... ✨</div>
          )}
        </header>
      </div>

      <div className="bottom-container">
        {guesses.length > 0 && (
          <main className="results">
            <ResultTable guesses={guesses} target={targetCharacter} />
          </main>
        )}
      </div>
    </div>
  );
}

export default App;