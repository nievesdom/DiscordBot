// compare.js
// Compara los datos de un personaje ingresado (user) con el objetivo (target)
// y devuelve un objeto con los resultados de cada campo.

export function compareCharacters(user, target) {
  
  // ------------------------------------------------------------------
  // Función auxiliar: normaliza "Unknown": devuelve null si es null, undefined o "unknown"
  // ------------------------------------------------------------------
  const normalizeUnknown = (v) => {
    if (!v) return null;
    if (typeof v === "string" && v.trim().toLowerCase() === "unknown") return null;
    return v;
  };

  // ------------------------------------------------------------------
  // Convierte un valor a array, normalizando "Unknown" a vacío
  // Si es null/undefined/unknown → []
  // Si es array → se normaliza cada elemento? (por simplicidad, asumimos que no hay arrays anidados)
  // Si es string → [valor normalizado]
  // ------------------------------------------------------------------
  const toArray = (val) => {
    const normalized = normalizeUnknown(val);
    if (!normalized) return [];
    if (Array.isArray(normalized)) return normalized;
    return [normalized];
  };

  // ------------------------------------------------------------------
  // Compara dos listas (arrays)
  // - Si ambas están vacías → "green"
  // - Si son idénticas (mismos elementos) → "green"
  // - Si hay al menos un elemento común → "yellow"
  // - Si no → "red"
  // ------------------------------------------------------------------
  const compareList = (a, b) => {
    const listA = a || [];
    const listB = b || [];
    if (listA.length === 0 && listB.length === 0) return "green";
    if (JSON.stringify(listA.sort()) === JSON.stringify(listB.sort())) return "green";
    if (listA.some(x => listB.includes(x))) return "yellow";
    return "red";
  };

  // ------------------------------------------------------------------
  // Compara dos valores simples (con normalización de "Unknown")
  // ------------------------------------------------------------------
  const compareValue = (a, b) => {
    const normA = normalizeUnknown(a);
    const normB = normalizeUnknown(b);
    if (normA === null && normB === null) return "green";
    if (normA === null || normB === null) return "red";
    if (normA === normB) return "green";
    return "red";
  };

  // ------------------------------------------------------------------
  // Extrae el primer número de una cadena (para altura)
  // ------------------------------------------------------------------
  const parseHeightNumber = (h) => {
    if (!h) return NaN;
    const match = h.match(/\d+/);
    return match ? parseInt(match[0]) : NaN;
  };

  // ------------------------------------------------------------------
  // Compara alturas
  // ------------------------------------------------------------------
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

  // ------------------------------------------------------------------
  // Extrae el primer año (4 dígitos) de una cadena de fecha
  // ------------------------------------------------------------------
  const parseYear = (dateStr) => {
    if (!dateStr) return null;
    const match = dateStr.match(/\b(1|2)\d{3}\b/);
    return match ? parseInt(match[0]) : null;
  };

  // ------------------------------------------------------------------
  // Compara fechas de nacimiento
  // ------------------------------------------------------------------
  const compareBirth = (a, b) => {
    const userNorm = normalizeUnknown(a);
    const targetNorm = normalizeUnknown(b);

    if (!userNorm && !targetNorm) return "green";
    if (!userNorm || !targetNorm) return "red";

    const dateA = new Date(userNorm);
    const dateB = new Date(targetNorm);
    const validA = !isNaN(dateA);
    const validB = !isNaN(dateB);

    if (validA && validB) {
      const sameDay = dateA.getDate() === dateB.getDate();
      const sameMonth = dateA.getMonth() === dateB.getMonth();
      const sameYear = dateA.getFullYear() === dateB.getFullYear();

      if (sameDay && sameMonth && sameYear) return "green";

      if (sameYear || (sameDay && sameMonth && !sameYear)) {
        return dateA < dateB ? "older" : "younger";
      }

      return dateA < dateB ? "red-older" : "red-younger";
    } else {
      const yearA = parseYear(userNorm);
      const yearB = parseYear(targetNorm);
      if (yearA && yearB) {
        if (yearA === yearB) return "green";
        return yearA < yearB ? "red-older" : "red-younger";
      }
      return "red";
    }
  };

  // ------------------------------------------------------------------
  // Compara listas de juegos, excluyendo "Ryu Ga Gotoku Online" para el color
  // ------------------------------------------------------------------
  const compareGames = (userGames, targetGames) => {
    const EXCLUDED = "Ryu Ga Gotoku Online";
    const userFiltered = (userGames || []).filter(g => g !== EXCLUDED);
    const targetFiltered = (targetGames || []).filter(g => g !== EXCLUDED);

    if (!userFiltered.length && !targetFiltered.length) return "red";
    if (JSON.stringify(userFiltered.sort()) === JSON.stringify(targetFiltered.sort())) return "green";
    if (userFiltered.some(x => targetFiltered.includes(x))) return "yellow";
    return "red";
  };

  // ------------------------------------------------------------------
  // Normaliza un estilo de lucha: elimina paréntesis y trata "Unknown"
  // ------------------------------------------------------------------
  const normalizeFightingStyle = (style) => {
    if (!style) return "";
    // Primero, convertir "Unknown" en vacío
    const noUnknown = normalizeUnknown(style);
    if (noUnknown === null) return "";
    // Luego eliminar paréntesis y su contenido
    return noUnknown.replace(/\s*\([^)]*\)/g, "").trim();
  };

  // ------------------------------------------------------------------
  // Compara estilos de lucha (con regla especial para "Legend")
  // ------------------------------------------------------------------
  const compareFightingStyles = (userStyles, targetStyles) => {
    const userList = userStyles || [];
    const targetList = targetStyles || [];

    // Normalizar y filtrar vacíos
    const userNorm = userList.map(normalizeFightingStyle).filter(s => s !== "");
    const targetNorm = targetList.map(normalizeFightingStyle).filter(s => s !== "");

    if (userNorm.length === 0 && targetNorm.length === 0) return "green";
    if (userNorm.length === 0 || targetNorm.length === 0) return "red";
    if (JSON.stringify(userNorm.sort()) === JSON.stringify(targetNorm.sort())) return "green";

    const userHasLegend = userNorm.some(style => style.includes("Legend"));
    const targetHasLegend = targetNorm.some(style => style.includes("Legend"));
    if (userHasLegend && targetHasLegend) return "yellow";

    if (userNorm.some(x => targetNorm.includes(x))) return "yellow";

    return "red";
  };

  // ------------------------------------------------------------------
  // Resultado final para cada campo
  // ------------------------------------------------------------------
  return {
    affiliation: compareList(user.affiliation || [], target.affiliation || []),
    nationality: compareList(toArray(user.nationality), toArray(target.nationality)),
    games: compareGames(user.appears_in || [], target.appears_in || []),
    blood_type: compareValue(user.blood_type, target.blood_type),
    fighting_style: compareFightingStyles(user.fighting_style || [], target.fighting_style || []),
    height: compareHeight(user.height, target.height),
    date_of_birth: compareBirth(user.date_of_birth, target.date_of_birth)
  };
}