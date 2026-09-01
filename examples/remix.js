// Pentagon Games Image Remix API — Node.js example (async: submit, then poll). Node 18+.
//   IMGEN_KEY=ef_xxx node remix.js my_pet.png "make it a knight in golden armor"
import { readFile, writeFile } from "node:fs/promises";

const BASE = process.env.IMGEN_BASE || "https://imgen.pentagon.games";
const KEY  = process.env.IMGEN_KEY;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function remix(imagePath, prompt, out = "derivative.png") {
  const form = new FormData();
  form.set("image", new Blob([await readFile(imagePath)]), imagePath.split(/[\\/]/).pop());
  form.set("prompt", prompt + ", keep it a creature with its animal head and body, not human");
  form.set("negative_prompt", "blurry, low quality, deformed, human face, human person");
  form.set("steps", "35");

  // 1) submit
  const sub = await fetch(`${BASE}/v1/edit`, { method: "POST", headers: { "x-api-key": KEY }, body: form });
  if (!sub.ok) throw new Error(`submit ${sub.status} ${await sub.text()}`);
  const { job_id } = await sub.json();
  console.log("job", job_id);

  // 2) poll until 200 (202 = still working)
  for (;;) {
    const r = await fetch(`${BASE}/v1/result/${job_id}`, { headers: { "x-api-key": KEY } });
    if (r.status === 200) { await writeFile(out, Buffer.from(await r.arrayBuffer())); console.log("saved", out); return; }
    if (r.status === 202) { await sleep(10000); continue; }
    throw new Error(`result ${r.status} ${await r.text()}`);
  }
}

const [imagePath, prompt] = process.argv.slice(2);
remix(imagePath, prompt).catch((e) => { console.error(e); process.exit(1); });
