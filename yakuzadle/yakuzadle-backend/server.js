import express from "express";
import cors from "cors";
import { db } from "./firestore.js";
import { compareCharacters } from "./compare.js";

const app = express();
app.use(cors());
app.use(express.json());

// Cache de nombres de personajes (se carga al iniciar)
let characterNames = [];
// Cache del personaje objetivo del día
let dailyTarget = {
  date: null, // string YYYY-MM-DD
  character: null
};

// Cargar todos los nombres de personajes desde Firestore
async function loadCharacterNames() {
  const snapshot = await db.collection("personajes").get();
  characterNames = snapshot.docs.map(doc => doc.id);
  console.log(`Loaded ${characterNames.length} character names`);
}

// Función para obtener el personaje objetivo de una fecha dada (por defecto hoy)
async function getDailyTarget(date = new Date()) {
  const utcDate = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dateStr = utcDate.toISOString().split('T')[0]; // YYYY-MM-DD

  // Si ya tenemos el personaje para hoy en caché, devolverlo
  if (dailyTarget.date === dateStr && dailyTarget.character) {
    return dailyTarget.character;
  }

  // Calcular el índice basado en el día del año
  const startOfYear = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  const diff = utcDate - startOfYear;
  const dayOfYear = Math.floor(diff / 86400000) + 1; // 1-366
  const index = (dayOfYear - 1) % characterNames.length;
  const targetName = characterNames[index];

  // Obtener el personaje de Firestore
  const doc = await db.collection("personajes").doc(targetName).get();
  if (!doc.exists) {
    throw new Error(`Target character ${targetName} not found in Firestore`);
  }
  const targetChar = doc.data();

  // Actualizar caché
  dailyTarget = {
    date: dateStr,
    character: targetChar
  };

  return targetChar;
}

// Endpoint para adivinar un personaje
app.get("/guess", async (req, res) => {
  const name = req.query.name;
  if (!name) return res.status(400).json({ error: "Missing name" });

  const userChar = await getCharacter(name);
  if (!userChar) return res.status(404).json({ error: "Character not found" });

  try {
    const targetChar = await getDailyTarget();
    const result = compareCharacters(userChar, targetChar);

    res.json({
      character: {
        ...userChar,
        games: userChar.appears_in
      },
      result,
      target: targetChar  // Incluimos el objetivo para que el frontend pueda usarlo
    });
  } catch (error) {
    console.error("Error getting daily target:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Endpoint para listar todos los personajes (con imagen para autocompletado)
app.get("/list", async (req, res) => {
  const snapshot = await db.collection("personajes").get();
  const items = snapshot.docs.map(doc => {
    const data = doc.data();
    const image = data.images && data.images.length > 0 ? data.images[0] : null;
    return {
      name: doc.id,
      image: image ? `https://raw.githubusercontent.com/nievesdom/DiscordBot/main/yakuzadle/img_yakuzadle/${image}` : null
    };
  });
  res.json(items);
});

// NUEVO ENDPOINT: Devuelve el personaje objetivo del día (solo el nombre, o datos completos si se necesita)
app.get("/daily-target", async (req, res) => {
  try {
    const target = await getDailyTarget();
    // Por ahora solo devolvemos el nombre, pero podríamos devolver más datos si el frontend los necesita
    res.json({ name: target.name });
  } catch (error) {
    console.error("Error fetching daily target:", error);
    res.status(500).json({ error: "Could not fetch daily target" });
  }
});

// Función auxiliar para obtener un personaje por nombre desde Firestore
async function getCharacter(name) {
  const doc = await db.collection("personajes").doc(name).get();
  return doc.exists ? doc.data() : null;
}

// Inicializar: cargar nombres y arrancar servidor
loadCharacterNames().then(() => {
  app.listen(3001, () => {
    console.log("Yakuzadle backend running on port 3001");
  });
}).catch(err => {
  console.error("Failed to load character names:", err);
  process.exit(1);
});