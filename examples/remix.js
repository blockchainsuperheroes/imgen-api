// Pentagon Games Image Remix API — Node.js example (Node 18+, native fetch/FormData/Blob).
//   IMGEN_KEY=ef_xxx node remix.js my_pet.png "make it a knight in golden armor"
import { readFile, writeFile } from "node:fs/promises";

const BASE = process.env.IMGEN_BASE || "https://imgen.pentagon.games";
const KEY  = process.env.IMGEN_KEY;

async function remix(imagePath, prompt, out = "derivative.png", params = {}) {
  const bytes = await readFile(imagePath);
  const form = new FormData();
  form.set("image", new Blob([bytes]), imagePath.split(/[\\/]/).pop());
  form.set("prompt", prompt + ", keep it a creature with its animal head and body, not human");
  form.set("negative_prompt", "blurry, low quality, deformed, human face, human person");
  form.set("steps", String(params.steps ?? 35));
  form.set("cfg",   String(params.cfg   ?? 4.0));
  form.set("seed",  String(params.seed  ?? 7));

  const res = await fetch(`${BASE}/v1/edit`, {
    method: "POST",
    headers: { "x-api-key": KEY },
    body: form,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  await writeFile(out, Buffer.from(await res.arrayBuffer()));
  console.log("saved", out);
}

const [imagePath, prompt] = process.argv.slice(2);
remix(imagePath, prompt).catch((e) => { console.error(e); process.exit(1); });
