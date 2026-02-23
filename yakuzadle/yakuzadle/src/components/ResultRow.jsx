function ResultRow({ guess, target }) {
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

  const normalizeFightingStyle = (style) => {
    if (!style) return "";
    return style.replace(/\s*\([^)]*\)/g, "").trim();
  };

  const imageUrl = guess.character?.images?.[0]
    ? `https://raw.githubusercontent.com/nievesdom/DiscordBot/main/yakuzadle/img_yakuzadle/${guess.character.images[0]}`
    : null;

  const EXCLUDED_GAME = "Ryu Ga Gotoku Online";
  const userGames = guess.character?.games || [];
  const targetGames = target?.appears_in || [];

  const renderGames = () => {
    if (!userGames.length) return "-";
    return userGames.map((game, idx) => {
      const isExcluded = game === EXCLUDED_GAME;
      const isBold = isExcluded && targetGames.includes(EXCLUDED_GAME);
      return (
        <span key={idx}>
          {idx > 0 && ", "}
          {isBold ? <strong>{game}</strong> : game}
        </span>
      );
    });
  };

  const totalCells = 8; // 1 (character) + 7 fields

  // Mapa de colores a códigos hexadecimales
  const colorMap = {
    green: '#2e7d32',
    yellow: '#d4a017',
    red: '#c62828',
    higher: '#c62828',
    lower: '#c62828',
    older: '#c62828',
    younger: '#c62828'
  };

  // Función para obtener el color final de una celda
  const getFinalColor = (key, comparisonColor) => {
    if (key === 'character') return '#333';
    return colorMap[comparisonColor] || '#333';
  };

  return (
    <div className="row">
      {/* Celda del personaje */}
      <div
        className="cell character-cell"
        style={{
          animationDelay: `${(totalCells - 1 - 0) * 0.15}s`,
          '--final-bg': '#333'
        }}
      >
        {imageUrl ? (
          <img src={imageUrl} alt={guess.name} className="character-image" />
        ) : (
          <div className="character-image-placeholder"></div>
        )}
        <span className="character-name">{guess.name}</span>
      </div>

      {fields.map(([key], i) => {
        const cellIndex = i + 1;
        const delay = (totalCells - 1 - cellIndex) * 0.15;

        // Determinar el color de comparación
        let comparisonColor = guess.comparison?.[key] || "red";
        if (key === "date_of_birth") {
          comparisonColor = colorForBirth(comparisonColor);
        }

        const finalBg = getFinalColor(key, comparisonColor);

        // Games
        if (key === "games") {
          return (
            <div
              key={i}
              className={`cell color-cell ${comparisonColor}`}
              style={{
                animationDelay: `${delay}s`,
                '--final-bg': finalBg
              }}
            >
              <span className="cell-text">{renderGames()}</span>
            </div>
          );
        }

        // Fighting style
        if (key === "fighting_style") {
          const value = guess.character?.[key];
          let text = "-";
          if (Array.isArray(value)) {
            const normalized = value.map(v => normalizeFightingStyle(v)).filter(v => v);
            text = normalized.length ? normalized.join(", ") : "-";
          } else if (typeof value === "string") {
            text = normalizeFightingStyle(value) || "-";
          }
          return (
            <div
              key={i}
              className={`cell color-cell ${comparisonColor}`}
              style={{
                animationDelay: `${delay}s`,
                '--final-bg': finalBg
              }}
            >
              <span className="cell-text">{text}</span>
            </div>
          );
        }

        // Resto de campos
        const value = guess.character?.[key];
        let text = "-";
        if (Array.isArray(value)) {
          text = value.length ? value.join(", ") : "-";
        } else if (typeof value === "string") {
          text = value;
        }

        return (
          <div
            key={i}
            className={`cell color-cell ${comparisonColor}`}
            style={{
              animationDelay: `${delay}s`,
              '--final-bg': finalBg
            }}
          >
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