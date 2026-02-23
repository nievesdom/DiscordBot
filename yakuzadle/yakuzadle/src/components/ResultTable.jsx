import { useEffect, useRef } from "react";
import ResultRow from "./ResultRow";

function ResultTable({ guesses, target }) {
  const tableRef = useRef(null);

  useEffect(() => {
    if (tableRef.current) {
      tableRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [guesses.length]);

  return (
    <div className="table">
      <div className="header-row">
        <div className="header-cell">Character</div>
        <div className="header-cell">Affiliation</div>
        <div className="header-cell">Nationality</div>
        <div className="header-cell">Games*</div>
        <div className="header-cell">Blood Type</div>
        <div className="header-cell">Fighting Style</div>
        <div className="header-cell">Height</div>
        <div className="header-cell">Birthdate</div>
      </div>

      {guesses.map((g, i) => (
        <ResultRow key={i} guess={g} target={target} />
      ))}

      <div ref={tableRef} />

      <div className="table-footer">
        * Ryu Ga Gotoku Online does not count for color comparison. If it matches, it appears in <strong>bold</strong>.
      </div>
    </div>
  );
}

export default ResultTable;