package main

// License handling for the API server: verifies GLE1 keys offline (same format as license/main.go),
// stores the activated key in <data>/license.key, and exposes /api/license for the lab page.

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// Must match license/main.go, grocery_eval/license.py and web/license.js.
const licensePublicKeyHex = "cdfee672299ee1b13ea0718511fdeb50aaf06d07daba24fecc44c6d75c080a01"
const licensePrefix = "GLE1-"

var trialQuestions = map[string]bool{"Q01": true, "Q05": true, "Q15": true, "Q28": true, "Q31": true, "Q36": true}

type LicensePayload struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Email   string `json:"email"`
	Plan    string `json:"plan"`
	Seats   int    `json:"seats"`
	Issued  string `json:"issued"`
	Expires string `json:"expires"`
}

func verifyLicense(key string) (*LicensePayload, error) {
	key = strings.TrimSpace(key)
	if !strings.HasPrefix(key, licensePrefix) {
		return nil, fmt.Errorf("key must start with %s", licensePrefix)
	}
	parts := strings.Split(strings.TrimPrefix(key, licensePrefix), ".")
	if len(parts) != 2 {
		return nil, fmt.Errorf("key has wrong shape")
	}
	body, err1 := base64.RawURLEncoding.DecodeString(parts[0])
	sig, err2 := base64.RawURLEncoding.DecodeString(parts[1])
	pub, err3 := hex.DecodeString(licensePublicKeyHex)
	if err1 != nil || err2 != nil || err3 != nil || len(pub) != ed25519.PublicKeySize || len(sig) != ed25519.SignatureSize {
		return nil, fmt.Errorf("key is not valid base64")
	}
	if !ed25519.Verify(ed25519.PublicKey(pub), body, sig) {
		return nil, fmt.Errorf("signature does not match: key was altered or issued for a different product")
	}
	var p LicensePayload
	if err := json.Unmarshal(body, &p); err != nil {
		return nil, fmt.Errorf("payload is not valid JSON")
	}
	return &p, nil
}

func licensePath() string { return filepath.Join(*dataDir, "license.key") }

// storedLicense looks in <data>/license.key, then ../license.key (project folder), then $GROCERY_LICENSE.
func storedLicense() string {
	for _, p := range []string{licensePath(), filepath.Join(filepath.Dir(*webDir), "license.key")} {
		if b, err := os.ReadFile(p); err == nil && strings.TrimSpace(string(b)) != "" {
			return strings.TrimSpace(string(b))
		}
	}
	return os.Getenv("GROCERY_LICENSE")
}

type licenseStatus struct {
	Licensed       bool            `json:"licensed"`
	Payload        *LicensePayload `json:"payload"`
	Reason         string          `json:"reason"`
	UpdatesExpired bool            `json:"updates_expired"`
	TrialQuestions []string        `json:"trial_questions"`
	TrialVariants  []string        `json:"trial_variants"`
}

func currentLicense() licenseStatus {
	st := licenseStatus{TrialQuestions: []string{"Q01", "Q05", "Q15", "Q28", "Q31", "Q36"}, TrialVariants: []string{"baseline"}}
	key := storedLicense()
	if key == "" {
		st.Reason = "no license key found (trial mode)"
		return st
	}
	p, err := verifyLicense(key)
	if err != nil {
		st.Reason = err.Error()
		return st
	}
	st.Licensed, st.Payload = true, p
	if t, err := time.Parse("2006-01-02", p.Expires); err == nil && t.Before(time.Now()) {
		st.UpdatesExpired = true
	}
	return st
}

func licenseHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, 200, currentLicense())
	case http.MethodPost:
		var req struct{ Key string }
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, 400, map[string]string{"error": "send {\"key\": \"GLE1-...\"}"})
			return
		}
		p, err := verifyLicense(req.Key)
		if err != nil {
			writeJSON(w, 400, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		os.MkdirAll(*dataDir, 0o755)
		if err := os.WriteFile(licensePath(), []byte(strings.TrimSpace(req.Key)+"\n"), 0o600); err != nil {
			writeJSON(w, 500, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		writeJSON(w, 200, map[string]interface{}{"ok": true, "payload": p, "path": licensePath()})
	case http.MethodDelete:
		os.Remove(licensePath())
		writeJSON(w, 200, map[string]interface{}{"ok": true, "licensed": false})
	default:
		writeJSON(w, 405, map[string]string{"error": "method not allowed"})
	}
}

// trialWatermark is prepended to exports when unlicensed.
func trialWatermark() string {
	if currentLicense().Licensed {
		return ""
	}
	return "TRIAL MODE - unlicensed copy of grocery-llm-eval. Activate at /lab.html or with `python activate.py <KEY>`.\n\n"
}
