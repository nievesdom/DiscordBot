import { useState, useEffect } from "react";
import GuessInput from "./components/GuessInput";
import ResultTable from "./components/ResultTable";
import Celebration from "./components/Celebration";
import Toast from "./components/Toast";
import { setDebugTarget } from "./services/api"; // nueva función
import "./styles/main.css";

function App() {
  const [guesses, setGuesses] = useState([]);
  const [targetCharacter, setTargetCharacter] = useState(null);
  const [gameWon, setGameWon] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [toast, setToast] = useState({ message: "", show: false });
  const [characterNames, setCharacterNames] = useState([]);

  // Cargar lista de nombres al inicio
  useEffect(() => {
    const cached = localStorage.getItem("characterList");
    if (cached) {
      setCharacterNames(JSON.parse(cached).map(item => item.name));
    } else {
      fetch("http://localhost:3001/list")
        .then(res => res.json())
        .then(data => {
          localStorage.setItem("characterList", JSON.stringify(data));
          setCharacterNames(data.map(item => item.name));
        })
        .catch(() => showToastMessage("Failed to load character list"));
    }
  }, []);

  const showToastMessage = (msg) => {
    setToast({ message: msg, show: true });
  };

  const handleGuess = async (name) => {
    try {
      const res = await fetch(
        `http://localhost:3001/guess?name=${encodeURIComponent(name)}`
      );
      const data = await res.json();

      if (data.error) {
        showToastMessage("Character not found");
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
          comparison: data.result,
        },
      ]);
      setAttempts((prev) => prev + 1);

      if (isCorrect && !gameWon) {
        setGameWon(true);
        const totalAnimationTime = 4000;
        setTimeout(() => {
          setShowCelebration(true);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }, totalAnimationTime);
      }
    } catch (error) {
      showToastMessage("Network error. Please try again.");
    }
  };

  const handlePlayAgain = () => {
    setGuesses([]);
    setGameWon(false);
    setShowCelebration(false);
    setAttempts(0);
  };

  // Función de depuración: elige un personaje aleatorio y lo establece como nuevo objetivo
  const handleDebugNewTarget = async () => {
    if (characterNames.length === 0) {
      showToastMessage("No characters loaded");
      return;
    }
    const randomName = characterNames[Math.floor(Math.random() * characterNames.length)];
    try {
      await setDebugTarget(randomName);
      // Resetear el juego
      setGuesses([]);
      setGameWon(false);
      setShowCelebration(false);
      setAttempts(0);
      setTargetCharacter(null); // Se volverá a cargar en el próximo guess
      showToastMessage(`New target set: ${randomName}`);
    } catch (error) {
      showToastMessage("Failed to set debug target");
    }
  };

  return (
    <div className="page">
      <div className="top-container">
        <header className="hero">
          <h1 className="title">Yakuzadle</h1>
          {!gameWon ? (
            <GuessInput onGuess={handleGuess} onError={showToastMessage} />
          ) : showCelebration ? (
            <Celebration onPlayAgain={handlePlayAgain} />
          ) : (
            <div className="waiting-message">✨ Revealing... ✨</div>
          )}
        </header>
        <div className="attempts-counter">
          Attempts: {attempts}
          {/* Botón de depuración solo visible en desarrollo */}
          {import.meta.env.DEV && (
            <button className="debug-button" onClick={handleDebugNewTarget} title="Set random target">
              🎲
            </button>
          )}
        </div>
      </div>

      <div className="bottom-container">
        {guesses.length > 0 && (
          <main className="results">
            <ResultTable guesses={guesses} target={targetCharacter} />
          </main>
        )}
      </div>

      {toast.show && (
        <Toast
          message={toast.message}
          onClose={() => setToast({ show: false, message: "" })}
        />
      )}
    </div>
  );
}

export default App;