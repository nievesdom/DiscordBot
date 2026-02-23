import { useState, useEffect } from "react";

function GuessInput({ onGuess }) {
  const [value, setValue] = useState("");
  const [allNames, setAllNames] = useState([]);
  const [filtered, setFiltered] = useState([]);

  useEffect(() => {
    fetch("http://localhost:3001/list")
      .then(res => res.json())
      .then(data => setAllNames(data));
  }, []);

  const handleChange = (e) => {
    const v = e.target.value;
    setValue(v);

    if (!v.length) {
      setFiltered([]);
      return;
    }

    const f = allNames.filter(n =>
      n.toLowerCase().includes(v.toLowerCase())
    );

    setFiltered(f.slice(0, 8));
  };

  const selectName = (name) => {
    setValue(name);
    setFiltered([]);
    onGuess(name);
  };

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    onGuess(value.trim());
    setValue("");
    setFiltered([]);
  };

  return (
    <div className="autocomplete-wrapper">
      <form onSubmit={submit} className="guess-form">
        <input
          type="text"
          placeholder="Type a character..."
          value={value}
          onChange={handleChange}
          className="guess-input"
        />
        <button className="guess-button">Guess</button>
      </form>

      {filtered.length > 0 && (
        <div className="autocomplete-box">
          {filtered.map((name, i) => (
            <div
              key={i}
              className="autocomplete-item"
              onClick={() => selectName(name)}
            >
              {name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GuessInput;
