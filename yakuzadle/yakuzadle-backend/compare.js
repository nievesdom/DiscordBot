export function compareCharacters(user, target) {
  // Función auxiliar para comparar listas (usada para affiliation, games, etc.)
  const compareList = (a, b) => {
    if (!a || !b) return "red";
    if (JSON.stringify(a) === JSON.stringify(b)) return "green";
    if (a.some(x => b.includes(x))) return "yellow";
    return "red";
  };

  // Comparación simple para valores únicos (nationality, blood_type)
  const compareValue = (a, b) => {
    if (!a || !b) return "red";
    if (a === b) return "green";
    return "red";
  };

  // Normaliza valores "Unknown"
  const normalizeUnknown = (v) => {
    if (!v) return null;
    if (typeof v === "string" && v.trim().toLowerCase() === "unknown") return null;
    return v;
  };

  // Para altura: extrae el número antes del paréntesis
  const parseHeightNumber = (h) => {
    if (!h) return NaN;
    const beforeParen = h.split("(")[0];
    const num = parseInt(beforeParen);
    return num;
  };

  const compareHeight = (a, b) => {
    a = normalizeUnknown(a);
    b = normalizeUnknown(b);

    if (!a && !b) return "green";

    const numA = parseHeightNumber(a);
    const numB = parseHeightNumber(b);

    if (isNaN(numA) || isNaN(numB)) return "red";
    if (numA === numB) return "green";
    return numA > numB ? "higher" : "lower";
  };

  const compareBirth = (a, b) => {
    if (!a || !b) return "red";

    const dateA = new Date(a);
    const dateB = new Date(b);

    if (isNaN(dateA) || isNaN(dateB)) return "red";

    const sameDay = dateA.getDate() === dateB.getDate();
    const sameMonth = dateA.getMonth() === dateB.getMonth();
    const sameYear = dateA.getFullYear() === dateB.getFullYear();

    if (sameDay && sameMonth && sameYear) return "green";

    if (sameYear || (sameDay && sameMonth && !sameYear)) {
      return dateA < dateB ? "older" : "younger";
    }

    return dateA < dateB ? "red-older" : "red-younger";
  };

  // Para games: excluye "Ryu Ga Gotoku Online" de la comparación de colores
  const compareGames = (userGames, targetGames) => {
    const EXCLUDED = "Ryu Ga Gotoku Online";

    const userFiltered = (userGames || []).filter(g => g !== EXCLUDED);
    const targetFiltered = (targetGames || []).filter(g => g !== EXCLUDED);

    if (!userFiltered.length && !targetFiltered.length) {
      return "red";
    }
    if (JSON.stringify(userFiltered.sort()) === JSON.stringify(targetFiltered.sort())) {
      return "green";
    }
    if (userFiltered.some(x => targetFiltered.includes(x))) {
      return "yellow";
    }
    return "red";
  };

  // NUEVA FUNCIÓN: Normaliza un string de fighting style eliminando paréntesis y su contenido
  const normalizeFightingStyle = (style) => {
    if (!style) return "";
    // Elimina cualquier texto entre paréntesis, incluidos los paréntesis
    return style.replace(/\s*\([^)]*\)/g, "").trim();
  };

  // Comparación para fighting_style: normaliza cada elemento antes de comparar
  const compareFightingStyles = (userStyles, targetStyles) => {
    if (!userStyles || !targetStyles) return "red";

    const userNorm = userStyles.map(normalizeFightingStyle).filter(s => s !== "");
    const targetNorm = targetStyles.map(normalizeFightingStyle).filter(s => s !== "");

    // Si ambos quedan vacíos después de normalizar, consideramos que no hay información
    if (userNorm.length === 0 && targetNorm.length === 0) {
      // Podría ser verde si ambos están vacíos (ambos unknown) pero mejor rojo
      return "red";
    }

    // Ahora comparamos las listas normalizadas con la misma lógica que compareList
    if (JSON.stringify(userNorm.sort()) === JSON.stringify(targetNorm.sort())) {
      return "green";
    }
    if (userNorm.some(x => targetNorm.includes(x))) {
      return "yellow";
    }
    return "red";
  };

  return {
    affiliation: compareList(user.affiliation || [], target.affiliation || []),
    nationality: compareValue(user.nationality, target.nationality),
    games: compareGames(user.appears_in || [], target.appears_in || []),
    blood_type: compareValue(user.blood_type, target.blood_type),
    fighting_style: compareFightingStyles(user.fighting_style || [], target.fighting_style || []),
    height: compareHeight(user.height, target.height),
    date_of_birth: compareBirth(user.date_of_birth, target.date_of_birth)
  };
}