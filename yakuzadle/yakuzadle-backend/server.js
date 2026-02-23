import express from "express";
import cors from "cors";
import { db } from "./firestore.js";
import { compareCharacters } from "./compare.js";

const app = express();
app.use(cors());
app.use(express.json());

const TARGET_NAME = "Hiroki Awano";

async function getCharacter(name) {
  const doc = await db.collection("personajes").doc(name).get();
  return doc.exists ? doc.data() : null;
}

app.get("/guess", async (req, res) => {
  const name = req.query.name;
  if (!name) return res.status(400).json({ error: "Missing name" });

  const userChar = await getCharacter(name);
  if (!userChar) return res.status(404).json({ error: "Character not found" });

  const targetChar = await getCharacter(TARGET_NAME);
  if (!targetChar) return res.status(500).json({ error: "Target not found" });

  const result = compareCharacters(userChar, targetChar);

  res.json({
    character: {
      ...userChar,
      games: userChar.appears_in
    },
    result
  });
});

app.get("/list", async (req, res) => {
  const snapshot = await db.collection("personajes").get();
  const names = snapshot.docs.map(doc => doc.id);
  res.json(names);
});

app.listen(3001, () => {
  console.log("Yakuzadle backend running on port 3001");
});
