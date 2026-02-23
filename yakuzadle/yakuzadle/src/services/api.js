export async function guessCharacter(name) {
  const res = await fetch(`http://localhost:3001/guess?name=${encodeURIComponent(name)}`);
  return res.json();
}
