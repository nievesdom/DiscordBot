import ResultRow from "./ResultRow";

function ResultTable({ guesses }) {
  return (
    <div className="table">
      <div className="header-row">
        <div className="header-cell">Name</div>
        <div className="header-cell">Affiliation</div>
        <div className="header-cell">Nationality</div>
        <div className="header-cell">Games</div>
        <div className="header-cell">Blood Type</div>
        <div className="header-cell">Fighting Style</div>
        <div className="header-cell">Height</div>
        <div className="header-cell">Birthdate</div>
      </div>

      {guesses.map((g, i) => (
        <ResultRow key={i} guess={g} />
      ))}
    </div>
  );
}

export default ResultTable;
