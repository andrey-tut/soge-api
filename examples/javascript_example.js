// Soge.dk API — minimal JavaScript client (Node 18+ or browser, native fetch).
// Get a key (free tier): https://soge.dk/pricing
//   SOGE_API_KEY=your_key node javascript_example.js

const API = "https://soge.dk/api/v1";
const KEY = (typeof process !== "undefined" && process.env.SOGE_API_KEY) || "your_key_here";

async function get(path, { params, auth = true } = {}) {
  const url = new URL(API + path);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const headers = auth ? { "X-API-KEY": KEY } : {};
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json();
}

(async () => {
  console.log("health  :", await get("/health", { auth: false }));
  console.log("vehicle :", await get("/vehicles/AB12345"));
  console.log("company :", await get("/companies/" + encodeURIComponent("novo nordisk"), { params: { size: 5 } }));
  console.log("at-addr :", await get("/companies-at-address", { params: { postnr: "1050" } }));
  // Premium (paid plan):
  // console.log("syn    :", await get("/koretoj/AB12345/inspections"));
})().catch((e) => console.error(e.message));
