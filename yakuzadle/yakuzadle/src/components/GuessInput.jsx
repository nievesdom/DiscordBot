import { useState, useEffect } from "react";

function GuessInput({ onGuess }) {
  const [value, setValue] = useState("");
  const [allItems, setAllItems] = useState([]);      // array de { name, image }
  const [filtered, setFiltered] = useState([]);

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
    setValue(item.name);
    setFiltered([]);
    onGuess(item.name);
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