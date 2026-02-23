function ResultRow({ guess }) {
  const fields = [
    ["affiliation", "Affiliation"],
    ["nationality", "Nationality"],
    ["games", "Games"],
    ["blood_type", "Blood Type"],
    ["fighting_style", "Fighting Style"],
    ["height", "Height"],
    ["date_of_birth", "Birthdate"]
  ];

  const arrowFor = (key, color) => {
    if (key === "height") {
      if (color.includes("higher")) return "↑";
      if (color.includes("lower")) return "↓";
    }
    if (key === "date_of_birth") {
      if (color.includes("older")) return "↑";
      if (color.includes("younger")) return "↓";
    }
    return "";
  };

  const colorForBirth = (rawColor) => {
    if (rawColor === "green") return "green";
    if (rawColor.includes("older") || rawColor.includes("younger")) {
      return rawColor.includes("red") ? "red" : "yellow";
    }
    return "red";
  };

  return (
    <div className="row">
      {/* Celda del nombre con fondo de encabezado (clase name-cell actualizada en CSS) */}
      <div className="cell name-cell">{guess.name}</div>

      {fields.map(([key], i) => {
        const value = guess.character?.[key];
        let color = guess.comparison?.[key] || "red";

        let text = "-";

        if (Array.isArray(value)) {
          text = value.length ? value.join(", ") : "-";
        } else if (typeof value === "string") {
          text = value;
        }

        if (key === "date_of_birth") {
          color = colorForBirth(color);
        }

        return (
          <div key={i} className={`cell color-cell ${color}`}>
            <span className="cell-text">
              {text} {arrowFor(key, guess.comparison?.[key])}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default ResultRow;