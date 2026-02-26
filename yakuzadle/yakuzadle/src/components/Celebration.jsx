import { useEffect } from 'react';
import confetti from 'canvas-confetti';

function Celebration({ onPlayAgain }) {
  useEffect(() => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
    setTimeout(() => {
      confetti({
        particleCount: 50,
        spread: 100,
        origin: { y: 0.5, x: 0.2 }
      });
      confetti({
        particleCount: 50,
        spread: 100,
        origin: { y: 0.5, x: 0.8 }
      });
    }, 250);
  }, []);

  return (
    <div className="celebration">
      <h2>🎉 Congratulations! 🎉</h2>
      <p>You guessed the character correctly!</p>
      <button onClick={onPlayAgain} className="guess-button">
        Play again
      </button>
    </div>
  );
}

export default Celebration;