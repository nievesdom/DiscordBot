function ResultRow({ guess, target }) {
  const fields = [
    ["affiliation", "Affiliation"],
    ["nationality", "Nationality/Heritage"],
    ["games", "Games"],
    ["blood_type", "Blood Type"],
    ["fighting_style", "Fighting Style"],
    ["height", "Height"],
    ["date_of_birth", "Birthdate"],
  ];

  // Flechas hacia el personaje objetivo
  const arrowFor = (key, color) => {
    if (key === "height") {
      if (color.includes("higher")) return "↓"; // adivinado más alto → objetivo más bajo
      if (color.includes("lower")) return "↑";   // adivinado más bajo → objetivo más alto
    }
    if (key === "date_of_birth") {
      if (color.includes("older")) return "↓";   // adivinado mayor → él es mayor (flecha abajo)
      if (color.includes("younger")) return "↑"; // adivinado más joven → flecha arriba
    }
    return "";
  };

  // Tooltip para altura y fecha
  const tooltipFor = (key, color) => {
    if (key === "height") {
      if (color.includes("higher")) return "Target is lower";
      if (color.includes("lower")) return "Target is higher";
    }
    if (key === "date_of_birth") {
      if (color.includes("older")) return "You are older";
      if (color.includes("younger")) return "You are younger";
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

  const groupGames = (games) => {
    const grouped = [];
    const used = new Set();

    for (let i = 0; i < games.length; i++) {
      if (used.has(i)) continue;
      const game = games[i];
      let paired = false;

      const match = game.match(/^Yakuza(?:\s+(\d+))?$/);
      if (match) {
        const num = match[1] || "";
        const kiwamiName = num ? `Yakuza Kiwami ${num}` : "Yakuza Kiwami";
        for (let j = i + 1; j < games.length; j++) {
          if (used.has(j)) continue;
          if (games[j] === kiwamiName) {
            grouped.push(`${game} / ${kiwamiName}`);
            used.add(i);
            used.add(j);
            paired = true;
            break;
          }
        }
      }
      if (!paired) {
        grouped.push(game);
        used.add(i);
      }
    }
    return grouped;
  };

  const groupedGames = groupGames(userGames);

  const renderGames = () => {
    if (!groupedGames.length) return null;
    return groupedGames.map((game, idx) => {
      const isExcluded = game.includes(EXCLUDED_GAME);
      const isBold = isExcluded && targetGames.includes(EXCLUDED_GAME);
      return (
        <div key={idx} className="list-item">
          <span className="bullet">•</span>
          {isBold ? <strong>{game}</strong> : game}
        </div>
      );
    });
  };

  const renderAffiliation = () => {
    const affiliations = guess.character?.affiliation || [];
    if (!affiliations.length) return null;
    return affiliations.map((aff, idx) => (
      <div key={idx} className="list-item">
        <span className="bullet">•</span>
        {aff}
      </div>
    ));
  };

  const renderFightingStyles = () => {
    const styles = guess.character?.fighting_style || [];
    if (!styles.length) return null;
    return styles.map((style, idx) => {
      const normalized = normalizeFightingStyle(style);
      return (
        <div key={idx} className="list-item">
          <span className="bullet">•</span>
          {normalized}
        </div>
      );
    });
  };

  const totalDataCells = fields.length;
  const delayStep = 0.3;
  const characterDelay = (totalDataCells - 1) * delayStep + 1.0;

  const isCorrect = target && guess.name === target.name;
  const characterFinalBg = isCorrect ? "#2e7d32" : "#c62828";

  return (
    <div className="row">
      <div
        className="character-cell-static"
        style={{
          animationDelay: `${characterDelay}s`,
          "--character-final-bg": characterFinalBg,
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
        const delay = i * delayStep;
        const rawColor = guess.comparison?.[key] || "red";
        let bgColor = rawColor;
        if (key === "date_of_birth") {
          bgColor = colorForBirth(rawColor);
        }

        const arrow = arrowFor(key, rawColor);
        const tooltip = tooltipFor(key, rawColor);

        if (key === "affiliation") {
          const content = renderAffiliation();
          return (
            <div
              key={i}
              className={`cell color-cell ${bgColor} ${content ? "left-align" : ""}`}
              style={{ animationDelay: `${delay}s` }}
            >
              <div className="cell-text">{content || "-"}</div>
            </div>
          );
        }

        if (key === "games") {
          const content = renderGames();
          return (
            <div
              key={i}
              className={`cell color-cell ${bgColor} ${content ? "left-align" : ""}`}
              style={{ animationDelay: `${delay}s` }}
            >
              <div className="cell-text">{content || "-"}</div>
            </div>
          );
        }

        if (key === "fighting_style") {
          const content = renderFightingStyles();
          return (
            <div
              key={i}
              className={`cell color-cell ${bgColor} ${content ? "left-align" : ""}`}
              style={{ animationDelay: `${delay}s` }}
            >
              <div className="cell-text">{content || "-"}</div>
            </div>
          );
        }

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
            className={`cell color-cell ${bgColor}`}
            style={{ animationDelay: `${delay}s` }}
            title={tooltip || undefined}
          >
            <span className="cell-text">
              {text} {arrow}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default ResultRow;