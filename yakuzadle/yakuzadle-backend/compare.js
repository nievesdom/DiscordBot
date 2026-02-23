export function compareCharacters(user, target) {
  const compareList = (a, b) => {
    if (!a || !b) return "red";
    if (JSON.stringify(a) === JSON.stringify(b)) return "green";
    if (a.some(x => b.includes(x))) return "yellow";
    return "red";
  };

  const compareValue = (a, b) => {
    if (!a || !b) return "red";
    if (a === b) return "green";
    return "red";
  };

  const normalizeUnknown = (v) => {
    if (!v) return null;
    if (typeof v === "string" && v.trim().toLowerCase() === "unknown") return null;
    return v;
  };

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

    // exacta
    if (sameDay && sameMonth && sameYear) return "green";

    // amarilla si: mismo año, o mismo día y mes (aunque año distinto)
    if (sameYear || (sameDay && sameMonth && !sameYear)) {
      return dateA < dateB ? "older" : "younger";
    }

    // roja: ni mismo año ni mismo día-mes
    return dateA < dateB ? "red-older" : "red-younger";
  };

  return {
    affiliation: compareList(user.affiliation || [], target.affiliation || []),
    nationality: compareValue(user.nationality, target.nationality),
    games: compareList(user.appears_in || [], target.appears_in || []),
    blood_type: compareValue(user.blood_type, target.blood_type),
    fighting_style: compareList(user.fighting_style || [], target.fighting_style || []),
    height: compareHeight(user.height, target.height),
    date_of_birth: compareBirth(user.date_of_birth, target.date_of_birth)
  };
}