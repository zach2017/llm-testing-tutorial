/* license.js - offline license-key verification in the browser (Ed25519 via BigInt, RFC 8032).
   Same key format and public key as license/main.go, server/license.go and grocery_eval/license.py. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GroceryLicense = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const PUBLIC_KEY_HEX = "cdfee672299ee1b13ea0718511fdeb50aaf06d07daba24fecc44c6d75c080a01";
  const PREFIX = "GLE1-";
  const TRIAL_QUESTIONS = ["Q01", "Q05", "Q15", "Q28", "Q31", "Q36"], TRIAL_VARIANTS = ["baseline"];

  // ---- SHA-512 (sync, so verification works without async plumbing; ~100 lines) -------------
  const K = ["428a2f98d728ae22","7137449123ef65cd","b5c0fbcfec4d3b2f","e9b5dba58189dbbc","3956c25bf348b538","59f111f1b605d019","923f82a4af194f9b","ab1c5ed5da6d8118","d807aa98a3030242","12835b0145706fbe","243185be4ee4b28c","550c7dc3d5ffb4e2","72be5d74f27b896f","80deb1fe3b1696b1","9bdc06a725c71235","c19bf174cf692694","e49b69c19ef14ad2","efbe4786384f25e3","0fc19dc68b8cd5b5","240ca1cc77ac9c65","2de92c6f592b0275","4a7484aa6ea6e483","5cb0a9dcbd41fbd4","76f988da831153b5","983e5152ee66dfab","a831c66d2db43210","b00327c898fb213f","bf597fc7beef0ee4","c6e00bf33da88fc2","d5a79147930aa725","06ca6351e003826f","142929670a0e6e70","27b70a8546d22ffc","2e1b21385c26c926","4d2c6dfc5ac42aed","53380d139d95b3df","650a73548baf63de","766a0abb3c77b2a8","81c2c92e47edaee6","92722c851482353b","a2bfe8a14cf10364","a81a664bbc423001","c24b8b70d0f89791","c76c51a30654be30","d192e819d6ef5218","d69906245565a910","f40e35855771202a","106aa07032bbd1b8","19a4c116b8d2d0c8","1e376c085141ab53","2748774cdf8eeb99","34b0bcb5e19b48a8","391c0cb3c5c95a63","4ed8aa4ae3418acb","5b9cca4f7763e373","682e6ff3d6b2b8a3","748f82ee5defb2fc","78a5636f43172f60","84c87814a1f0ab72","8cc702081a6439ec","90befffa23631e28","a4506cebde82bde9","bef9a3f7b2c67915","c67178f2e372532b","ca273eceea26619c","d186b8c721c0c207","eada7dd6cde0eb1e","f57d4f7fee6ed178","06f067aa72176fba","0a637dc5a2c898a6","113f9804bef90dae","1b710b35131c471b","28db77f523047d84","32caab7b40c72493","3c9ebe0a15c9bebc","431d67c49c100d4c","4cc5d4becb3e42b6","597f299cfc657e2a","5fcb6fab3ad6faec","6c44198c4a475817"].map((h) => BigInt("0x" + h));
  const H0 = ["6a09e667f3bcc908","bb67ae8584caa73b","3c6ef372fe94f82b","a54ff53a5f1d36f1","510e527fade682d1","9b05688c2b3e6c1f","1f83d9abfb41bd6b","5be0cd19137e2179"].map((h) => BigInt("0x" + h));
  const M64 = (1n << 64n) - 1n;
  const rotr = (x, n) => ((x >> n) | (x << (64n - n))) & M64;
  function sha512(bytes) {
    const l = bytes.length, padLen = ((l + 17 + 127) >> 7) << 7;
    const m = new Uint8Array(padLen); m.set(bytes); m[l] = 0x80;
    const bits = BigInt(l) * 8n;
    for (let i = 0; i < 16; i++) m[padLen - 1 - i] = Number((bits >> BigInt(8 * i)) & 0xffn);
    const H = H0.slice(), W = new Array(80);
    for (let off = 0; off < padLen; off += 128) {
      for (let t = 0; t < 16; t++) { let v = 0n; for (let j = 0; j < 8; j++) v = (v << 8n) | BigInt(m[off + t * 8 + j]); W[t] = v; }
      for (let t = 16; t < 80; t++) {
        const s0 = rotr(W[t - 15], 1n) ^ rotr(W[t - 15], 8n) ^ (W[t - 15] >> 7n), s1 = rotr(W[t - 2], 19n) ^ rotr(W[t - 2], 61n) ^ (W[t - 2] >> 6n);
        W[t] = (W[t - 16] + s0 + W[t - 7] + s1) & M64;
      }
      let [a, b, c, d, e, f, g, h] = H;
      for (let t = 0; t < 80; t++) {
        const S1 = rotr(e, 14n) ^ rotr(e, 18n) ^ rotr(e, 41n), ch = (e & f) ^ (~e & M64 & g), t1 = (h + S1 + ch + K[t] + W[t]) & M64;
        const S0 = rotr(a, 28n) ^ rotr(a, 34n) ^ rotr(a, 39n), maj = (a & b) ^ (a & c) ^ (b & c), t2 = (S0 + maj) & M64;
        h = g; g = f; f = e; e = (d + t1) & M64; d = c; c = b; b = a; a = (t1 + t2) & M64;
      }
      H[0] = (H[0] + a) & M64; H[1] = (H[1] + b) & M64; H[2] = (H[2] + c) & M64; H[3] = (H[3] + d) & M64; H[4] = (H[4] + e) & M64; H[5] = (H[5] + f) & M64; H[6] = (H[6] + g) & M64; H[7] = (H[7] + h) & M64;
    }
    const out = new Uint8Array(64);
    H.forEach((v, i) => { for (let j = 0; j < 8; j++) out[i * 8 + j] = Number((v >> BigInt(56 - 8 * j)) & 0xffn); });
    return out;
  }

  // ---- Ed25519 ------------------------------------------------------------------------------
  const P = (1n << 255n) - 19n, L = (1n << 252n) + 27742317777372353535851937790883648493n;
  const mod = (a, m = P) => ((a % m) + m) % m;
  function pow(b, e, m = P) { let r = 1n; b = mod(b, m); while (e > 0n) { if (e & 1n) r = (r * b) % m; b = (b * b) % m; e >>= 1n; } return r; }
  const D = mod(-121665n * pow(121666n, P - 2n)), I = pow(2n, (P - 1n) / 4n);
  function xrecover(y) { const xx = mod((y * y - 1n) * pow(D * y * y + 1n, P - 2n)); let x = pow(xx, (P + 3n) / 8n); if (mod(x * x - xx) !== 0n) x = mod(x * I); if (x & 1n) x = P - x; return x; }
  const BY = mod(4n * pow(5n, P - 2n)), BX = xrecover(BY), B = [BX, BY, 1n, mod(BX * BY)];
  function add(p, q) { const [x1, y1, z1, t1] = p, [x2, y2, z2, t2] = q; const a = mod((y1 - x1) * (y2 - x2)), b = mod((y1 + x1) * (y2 + x2)), c = mod(t1 * 2n * D * t2), d = mod(z1 * 2n * z2); const e = b - a, f = d - c, g = d + c, h = b + a; return [mod(e * f), mod(g * h), mod(f * g), mod(e * h)]; }
  function mul(p, e) { let q = [0n, 1n, 1n, 0n]; while (e > 0n) { if (e & 1n) q = add(q, p); p = add(p, p); e >>= 1n; } return q; }
  const leToBig = (bytes) => { let v = 0n; for (let i = bytes.length - 1; i >= 0; i--) v = (v << 8n) | BigInt(bytes[i]); return v; };
  function decodePoint(s) { const y = leToBig(s) & ((1n << 255n) - 1n); let x = xrecover(y); if ((x & 1n) !== BigInt(s[31] >> 7)) x = P - x; if (mod(-x * x + y * y - 1n - D * x * x * y * y) !== 0n) throw new Error("not on curve"); return [x, y, 1n, mod(x * y)]; }
  const equal = (p, q) => mod(p[0] * q[2] - q[0] * p[2]) === 0n && mod(p[1] * q[2] - q[1] * p[2]) === 0n;
  function verify(pub, msg, sig) {
    if (pub.length !== 32 || sig.length !== 64) return false;
    let A, R; try { A = decodePoint(pub); R = decodePoint(sig.slice(0, 32)); } catch (e) { return false; }
    const s = leToBig(sig.slice(32)); if (s >= L) return false;
    const h = mod(leToBig(sha512(concat(sig.slice(0, 32), pub, msg))), L);
    return equal(mul(B, s), add(R, mul(A, h)));
  }
  function concat(...arrs) { const n = arrs.reduce((a, b) => a + b.length, 0), out = new Uint8Array(n); let o = 0; for (const a of arrs) { out.set(a, o); o += a.length; } return out; }
  function unb64(s) { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; const bin = (typeof atob === "function") ? atob(s) : Buffer.from(s, "base64").toString("binary"); const out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }
  const hexToBytes = (h) => new Uint8Array(h.match(/../g).map((x) => parseInt(x, 16)));

  // ---- key handling -------------------------------------------------------------------------
  function verifyKey(key, pubHex) {
    key = (key || "").trim();
    if (!key.startsWith(PREFIX)) return { payload: null, reason: "key must start with " + PREFIX };
    const parts = key.slice(PREFIX.length).split(".");
    if (parts.length !== 2) return { payload: null, reason: "key has wrong shape" };
    let body, sig; try { body = unb64(parts[0]); sig = unb64(parts[1]); } catch (e) { return { payload: null, reason: "key is not valid base64" }; }
    if (!verify(hexToBytes(pubHex || PUBLIC_KEY_HEX), body, sig)) return { payload: null, reason: "signature does not match: key was altered or issued for a different product" };
    try { return { payload: JSON.parse(new TextDecoder().decode(body)), reason: "" }; } catch (e) { return { payload: null, reason: "payload is not valid JSON" }; }
  }
  function updatesExpired(payload) { try { return new Date(payload.expires + "T23:59:59Z") < new Date(); } catch (e) { return false; } }
  return { PUBLIC_KEY_HEX, PREFIX, TRIAL_QUESTIONS, TRIAL_VARIANTS, verifyKey, updatesExpired, sha512 };
});
