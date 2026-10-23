// licensetool - issue and verify license keys for grocery-llm-eval, and (optionally) run a tiny
// activation server that records who activated what.
//
// Keys are Ed25519-signed, so the product can verify them OFFLINE with only the public key.
// Customers never need to reach a server; the server is just a ledger for the seller.
//
//	go run . keygen                                  # once: writes seller_private.key + public key (paste into the product)
//	go run . issue -name "Jane Doe" -email jane@x.com -plan personal -years 1
//	go run . verify GLE1-...                         # check a key
//	go run . serve -addr :9090                       # optional activation ledger (POST /activate, GET /activations)
//
// Key format:  GLE1-<base64url(JSON payload)>.<base64url(64-byte signature)>
// Payload:     {"id":"...","name":"...","email":"...","plan":"personal","seats":1,"issued":"2026-10-23","expires":"2027-10-23"}
// "expires" governs updates/support entitlement; the software itself keeps working (see docs/GO_TO_MARKET.md).
package main

import (
	"bufio"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const prefix = "GLE1-"

// PublicKeyHex is the seller's public key. `keygen` prints the value to paste here AND into
// server/license.go, grocery_eval/license.py and web/license.js (they must all match).
// The value below is a DEMO key whose private half ships in demo_private.key so you can try the
// whole flow; replace it with your own before selling (see docs/GO_TO_MARKET.md step 3).
var PublicKeyHex = "cdfee672299ee1b13ea0718511fdeb50aaf06d07daba24fecc44c6d75c080a01"

type Payload struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Email   string `json:"email"`
	Plan    string `json:"plan"`
	Seats   int    `json:"seats"`
	Issued  string `json:"issued"`
	Expires string `json:"expires"`
}

func b64(b []byte) string   { return base64.RawURLEncoding.EncodeToString(b) }
func unb64(s string) []byte { b, _ := base64.RawURLEncoding.DecodeString(s); return b }

func issue(priv ed25519.PrivateKey, p Payload) string {
	body, _ := json.Marshal(p)
	sig := ed25519.Sign(priv, body)
	return prefix + b64(body) + "." + b64(sig)
}

// Verify checks the signature and returns the payload. It does not check dates; callers decide
// what an expired "updates" date means (we keep the software working).
func Verify(key string, pubHex string) (*Payload, error) {
	key = strings.TrimSpace(key)
	if !strings.HasPrefix(key, prefix) {
		return nil, fmt.Errorf("key must start with %s", prefix)
	}
	parts := strings.Split(strings.TrimPrefix(key, prefix), ".")
	if len(parts) != 2 {
		return nil, fmt.Errorf("key has wrong shape")
	}
	pub, err := hex.DecodeString(pubHex)
	if err != nil || len(pub) != ed25519.PublicKeySize {
		return nil, fmt.Errorf("product public key is not configured")
	}
	body, sig := unb64(parts[0]), unb64(parts[1])
	if len(sig) != ed25519.SignatureSize || !ed25519.Verify(ed25519.PublicKey(pub), body, sig) {
		return nil, fmt.Errorf("signature does not match: key was altered or issued for a different product")
	}
	var p Payload
	if err := json.Unmarshal(body, &p); err != nil {
		return nil, fmt.Errorf("payload is not valid JSON")
	}
	return &p, nil
}

func loadPrivate(path string) ed25519.PrivateKey {
	b, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("cannot read private key %s (run `keygen` first): %v", path, err)
	}
	raw, err := hex.DecodeString(strings.TrimSpace(string(b)))
	if err != nil || len(raw) != ed25519.PrivateKeySize {
		log.Fatalf("private key file is malformed")
	}
	return ed25519.PrivateKey(raw)
}

func randomID() string {
	b := make([]byte, 5)
	rand.Read(b)
	return strings.ToUpper(hex.EncodeToString(b))
}

// ---------------------------------------------------------------- activation ledger (optional)

type activation struct {
	Key     string `json:"key_id"`
	Name    string `json:"name"`
	Email   string `json:"email"`
	Machine string `json:"machine"`
	Product string `json:"product_version"`
	Time    string `json:"time"`
	IP      string `json:"ip"`
}

func serve(addr, pubHex, ledgerPath string) {
	var mu sync.Mutex
	revoked := map[string]bool{}
	if b, err := os.ReadFile(filepath.Join(filepath.Dir(ledgerPath), "revoked.txt")); err == nil {
		for _, l := range strings.Split(string(b), "\n") {
			if l = strings.TrimSpace(l); l != "" {
				revoked[l] = true
			}
		}
	}
	http.HandleFunc("/activate", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			return
		}
		var req struct{ Key, Machine, ProductVersion string }
		json.NewDecoder(r.Body).Decode(&req)
		p, err := Verify(req.Key, pubHex)
		w.Header().Set("Content-Type", "application/json")
		if err != nil {
			json.NewEncoder(w).Encode(map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		if revoked[p.ID] {
			json.NewEncoder(w).Encode(map[string]interface{}{"ok": false, "error": "this license has been revoked (refunded?)"})
			return
		}
		a := activation{p.ID, p.Name, p.Email, req.Machine, req.ProductVersion, time.Now().UTC().Format(time.RFC3339), r.RemoteAddr}
		mu.Lock()
		f, _ := os.OpenFile(ledgerPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
		json.NewEncoder(f).Encode(a)
		f.Close()
		mu.Unlock()
		json.NewEncoder(w).Encode(map[string]interface{}{"ok": true, "license": p})
	})
	http.HandleFunc("/activations", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		var out []activation
		if f, err := os.Open(ledgerPath); err == nil {
			s := bufio.NewScanner(f)
			for s.Scan() {
				var a activation
				if json.Unmarshal(s.Bytes(), &a) == nil {
					out = append(out, a)
				}
			}
			f.Close()
		}
		json.NewEncoder(w).Encode(map[string]interface{}{"activations": out, "count": len(out)})
	})
	log.Printf("activation ledger listening on %s (ledger %s). Revoke a key by adding its id to revoked.txt and restarting.", addr, ledgerPath)
	log.Fatal(http.ListenAndServe(addr, nil))
}

// ---------------------------------------------------------------- CLI

func main() {
	if len(os.Args) < 2 {
		fmt.Println("usage: licensetool keygen | issue | verify <key> | serve")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "keygen":
		fs := flag.NewFlagSet("keygen", flag.ExitOnError)
		out := fs.String("out", "seller_private.key", "where to write the PRIVATE key (keep secret, back it up)")
		fs.Parse(os.Args[2:])
		if _, err := os.Stat(*out); err == nil {
			log.Fatalf("%s already exists; refusing to overwrite", *out)
		}
		pub, priv, _ := ed25519.GenerateKey(rand.Reader)
		os.WriteFile(*out, []byte(hex.EncodeToString(priv)+"\n"), 0o600)
		fmt.Printf("Private key written to %s  (NEVER ship this file; add it to .gitignore)\n\n", *out)
		fmt.Printf("Public key (paste into license/main.go, server/license.go, grocery_eval/license.py, web/license.js):\n%s\n", hex.EncodeToString(pub))
	case "issue":
		fs := flag.NewFlagSet("issue", flag.ExitOnError)
		keyPath := fs.String("key", "seller_private.key", "private key file")
		name := fs.String("name", "", "customer name")
		email := fs.String("email", "", "customer email")
		plan := fs.String("plan", "personal", "personal | team")
		seats := fs.Int("seats", 1, "number of users")
		years := fs.Int("years", 1, "years of updates and support")
		fs.Parse(os.Args[2:])
		if *name == "" || *email == "" {
			log.Fatal("-name and -email are required")
		}
		now := time.Now().UTC()
		p := Payload{ID: randomID(), Name: *name, Email: *email, Plan: *plan, Seats: *seats, Issued: now.Format("2006-01-02"), Expires: now.AddDate(*years, 0, 0).Format("2006-01-02")}
		key := issue(loadPrivate(*keyPath), p)
		fmt.Println(key)
		f, _ := os.OpenFile("issued_keys.jsonl", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o600)
		json.NewEncoder(f).Encode(map[string]interface{}{"payload": p, "key": key, "issued_at": now.Format(time.RFC3339)})
		f.Close()
		fmt.Fprintln(os.Stderr, "(recorded in issued_keys.jsonl)")
	case "verify":
		if len(os.Args) < 3 {
			log.Fatal("usage: licensetool verify <key>")
		}
		pubHex := PublicKeyHex
		if v := os.Getenv("GLE_PUBLIC_KEY"); v != "" {
			pubHex = v
		}
		p, err := Verify(os.Args[2], pubHex)
		if err != nil {
			fmt.Println("INVALID:", err)
			os.Exit(1)
		}
		b, _ := json.MarshalIndent(p, "", "  ")
		fmt.Printf("VALID\n%s\n", b)
	case "serve":
		fs := flag.NewFlagSet("serve", flag.ExitOnError)
		addr := fs.String("addr", ":9090", "listen address")
		ledger := fs.String("ledger", "activations.jsonl", "ledger file")
		fs.Parse(os.Args[2:])
		pubHex := PublicKeyHex
		if v := os.Getenv("GLE_PUBLIC_KEY"); v != "" {
			pubHex = v
		}
		serve(*addr, pubHex, *ledger)
	default:
		fmt.Println("unknown command", os.Args[1])
		os.Exit(2)
	}
}
