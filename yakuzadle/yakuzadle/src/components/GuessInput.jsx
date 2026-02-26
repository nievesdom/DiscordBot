import { useState, useEffect, useRef } from "react";

function GuessInput({ onGuess }) {
  const [value, setValue] = useState("");
  const [allItems, setAllItems] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch("http://localhost:3001/list")
      .then(res => res.json())
      .then(data => setAllItems(data));
  }, []);

  const handleChange = (e) => {
    const v = e.target.value;
    setValue(v);
    if (!v.length) {
      setFiltered([]);
      return;
    }
    const f = allItems.filter(item =>
      item.name.toLowerCase().includes(v.toLowerCase())
    );
    setFiltered(f.slice(0, 8));
  };

  const selectItem = (item) => {
    setFiltered([]);
    onGuess(item.name);
    setValue("");
    inputRef.current?.focus();
  };

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    onGuess(value.trim());
    setValue("");
    setFiltered([]);
    inputRef.current?.focus();
  };

  return (
    <div className="autocomplete-wrapper">
      <form onSubmit={submit} className="guess-form">
        <input
          ref={inputRef}
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
          {filtered.map((item, i) => (
            <div
              key={i}
              className="autocomplete-item"
              onClick={() => selectItem(item)}
            >
              {item.image ? (
                <img src={item.image} alt={item.name} className="suggestion-img" />
              ) : (
                <div className="suggestion-img-placeholder"></div>
              )}
              <span>{item.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GuessInput;