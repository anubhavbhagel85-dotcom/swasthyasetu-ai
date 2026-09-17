// Keeps the frontend's offline copy of the knowledge base and red-flag list
// in sync with the single source of truth in backend/app/data/.
// Run automatically before `dev` and `build` (see package.json).
import { copyFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BACKEND_DATA = path.resolve(__dirname, "../../backend/app/data");
const FRONTEND_OFFLINE = path.resolve(__dirname, "../src/offline");

mkdirSync(FRONTEND_OFFLINE, { recursive: true });

const files = ["knowledge_base.json", "red_flags.json"];

for (const file of files) {
  const src = path.join(BACKEND_DATA, file);
  const dest = path.join(FRONTEND_OFFLINE, file);
  try {
    copyFileSync(src, dest);
    console.log(`[sync-knowledge-base] copied ${file}`);
  } catch (err) {
    console.warn(
      `[sync-knowledge-base] could not copy ${file} from ${src} — using whatever copy already exists in src/offline/ (${err.message})`
    );
  }
}
