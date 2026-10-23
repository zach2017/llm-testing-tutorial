// grocery-llm-eval API server.
//
// A small, dependency-free Go server that:
//   - serves the web/ pages (tutorial + live lab) at http://localhost:8080
//   - forwards /api/ollama/* to a local Ollama (so the browser never hits CORS)
//   - saves runs posted by the lab (or by anything else) as JSON files under data/runs/
//   - exports any run as Markdown, JSON, CSV, printable HTML, or PDF
//
// Run:  go run .            (flags: -addr :8080 -ollama http://localhost:11434 -web ../web -data ./data)
package main

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const version = "1.0.0"

var (
	addr      = flag.String("addr", ":8080", "address to listen on")
	ollamaURL = flag.String("ollama", envOr("OLLAMA_HOST", "http://localhost:11434"), "Ollama base URL")
	webDir    = flag.String("web", "../web", "folder with index.html / lab.html")
	dataDir   = flag.String("data", "./data", "folder where runs are saved")
	activate  = flag.String("activate", "", "activate a license key (GLE1-...) and exit")
	safeID    = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,80}$`)
)

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		if !strings.HasPrefix(v, "http") {
			v = "http://" + v
		}
		return v
	}
	return d
}

// ---------------------------------------------------------------- data model (mirrors the lab's run object)

type Row struct {
	QuestionID       string   `json:"question_id"`
	Variant          string   `json:"variant"`
	Repeat           int      `json:"repeat"`
	Category         string   `json:"category"`
	Question         string   `json:"question"`
	ExpectedResponse string   `json:"expected_response"`
	RawResponse      string   `json:"raw_response"`
	FinalAnswer      string   `json:"final_answer"`
	Thinking         string   `json:"thinking"`
	Correct          bool     `json:"correct"`
	Score            float64  `json:"score"`
	FailureMode      string   `json:"failure_mode"`
	ScoringDetail    string   `json:"scoring_detail"`
	Refused          bool     `json:"refused"`
	LatencyS         *float64 `json:"latency_s"`
	CompletionTokens *int     `json:"completion_tokens"`
	TokensPerS       *float64 `json:"tokens_per_s"`
	DoneReason       string   `json:"done_reason"`
	Error            *string  `json:"error"`
}

type Run struct {
	ID          string                 `json:"id"`
	StartedAt   string                 `json:"started_at"`
	FinishedAt  string                 `json:"finished_at,omitempty"`
	Model       string                 `json:"model"`
	Host        string                 `json:"host"`
	Route       string                 `json:"route"`
	Settings    map[string]interface{} `json:"settings"`
	Variants    []string               `json:"variants"`
	QuestionIDs []string               `json:"question_ids"`
	Rows        []Row                  `json:"rows"`
	Finished    bool                   `json:"finished"`
	SavedAt     string                 `json:"saved_at,omitempty"`
}

var failureHelp = map[string]string{
	"wrong_value": "a number was given, but the wrong one", "wrong_entity": "a name / option / yes-no was given, but the wrong one",
	"partial": "list answer with some but not all items", "no_answer": "nothing scoreable in the response",
	"hallucination": "answered an unanswerable question with a specific claim", "over_refusal": "said the text lacked the answer when it was there",
	"premise_accepted": "went along with a false premise instead of correcting it", "format_violation": "right content, wrong output format", "error": "API error / timeout",
}

// ---------------------------------------------------------------- summary statistics

type Group struct{ N, K int }

func (g Group) Acc() float64 {
	if g.N == 0 {
		return 0
	}
	return float64(g.K) / float64(g.N)
}

type Summary struct {
	N, K                                int
	Acc, Lo, Hi                         float64
	Hallucination, OverRefusal, Premise *float64
	ByCategory, ByVariant               map[string]*Group
	CategoryOrder, VariantOrder         []string
	FailureModes                        map[string]int
	FailureOrder                        []string
	MedianLatency, MeanTPS              *float64
}

func wilson(k, n int) (float64, float64) {
	if n == 0 {
		return 0, 0
	}
	z, p := 1.96, float64(k)/float64(n)
	nn := float64(n)
	d := 1 + z*z/nn
	c := (p + z*z/(2*nn)) / d
	h := z * sqrt(p*(1-p)/nn+z*z/(4*nn*nn)) / d
	return max(0, c-h), min(1, c+h)
}

func sqrt(x float64) float64 { // Newton's method; avoids importing math for one call (kept tiny on purpose)
	if x <= 0 {
		return 0
	}
	r := x
	for i := 0; i < 40; i++ {
		r = (r + x/r) / 2
	}
	return r
}

func rate(num, den int) *float64 {
	if den == 0 {
		return nil
	}
	v := float64(num) / float64(den)
	return &v
}

func summarize(run *Run) Summary {
	s := Summary{ByCategory: map[string]*Group{}, ByVariant: map[string]*Group{}, FailureModes: map[string]int{}}
	var unansN, unansWrong, premN, premAcc, ansN, ansOver int
	var lats, tps []float64
	for _, r := range run.Rows {
		if r.FailureMode != "" {
			s.FailureModes[r.FailureMode]++
		}
		if r.Variant == "no_context" {
			continue
		}
		s.N++
		if r.Correct {
			s.K++
		}
		for _, gk := range []struct {
			m   map[string]*Group
			key string
		}{{s.ByCategory, r.Category}, {s.ByVariant, r.Variant}} {
			if gk.m[gk.key] == nil {
				gk.m[gk.key] = &Group{}
			}
			gk.m[gk.key].N++
			if r.Correct {
				gk.m[gk.key].K++
			}
		}
		switch r.Category {
		case "unanswerable":
			unansN++
			if !r.Correct {
				unansWrong++
			}
		case "false_premise":
			premN++
			if r.FailureMode == "premise_accepted" {
				premAcc++
			}
		default:
			ansN++
			if r.Refused && !r.Correct {
				ansOver++
			}
		}
		if r.LatencyS != nil {
			lats = append(lats, *r.LatencyS)
		}
		if r.TokensPerS != nil {
			tps = append(tps, *r.TokensPerS)
		}
	}
	s.Acc = Group{s.N, s.K}.Acc()
	s.Lo, s.Hi = wilson(s.K, s.N)
	s.Hallucination, s.Premise, s.OverRefusal = rate(unansWrong, unansN), rate(premAcc, premN), rate(ansOver, ansN)
	for k := range s.ByCategory {
		s.CategoryOrder = append(s.CategoryOrder, k)
	}
	for k := range s.ByVariant {
		s.VariantOrder = append(s.VariantOrder, k)
	}
	for k := range s.FailureModes {
		s.FailureOrder = append(s.FailureOrder, k)
	}
	sort.Strings(s.CategoryOrder)
	sort.Strings(s.VariantOrder)
	sort.Strings(s.FailureOrder)
	if len(lats) > 0 {
		sort.Float64s(lats)
		m := lats[len(lats)/2]
		s.MedianLatency = &m
	}
	if len(tps) > 0 {
		t := 0.0
		for _, v := range tps {
			t += v
		}
		t /= float64(len(tps))
		s.MeanTPS = &t
	}
	return s
}

func pct(x float64) string { return fmt.Sprintf("%.1f%%", 100*x) }
func pctP(x *float64) string {
	if x == nil {
		return "n/a"
	}
	return pct(*x)
}
func fsec(x *float64) string {
	if x == nil {
		return "n/a"
	}
	return fmt.Sprintf("%.1f s", *x)
}
func f1(x *float64) string {
	if x == nil {
		return "n/a"
	}
	return fmt.Sprintf("%.1f", *x)
}
func oneLine(s string, n int) string {
	s = strings.Join(strings.Fields(s), " ")
	if len(s) > n {
		return s[:n-1] + "…"
	}
	return s
}
func settingStr(run *Run, k string) string {
	if v, ok := run.Settings[k]; ok && v != nil && v != "" {
		return fmt.Sprint(v)
	}
	return "default"
}

// ---------------------------------------------------------------- Markdown export

func runMarkdown(run *Run) string {
	s := summarize(run)
	var b strings.Builder
	w := func(f string, a ...interface{}) { fmt.Fprintf(&b, f+"\n", a...) }
	status := ""
	if !run.Finished {
		status = " (incomplete)"
	}
	w("# Grocery-Store Benchmark — %s\n", run.Model)
	if wm := trialWatermark(); wm != "" {
		w("> %s", strings.TrimSpace(wm))
	}
	w("Run %s, started %s%s. Settings: max tokens %s, temperature %s, thinking %s, repeats %s. Connection: %s. Prompt styles: %s.\n",
		run.ID, run.StartedAt, status, settingStr(run, "num_predict"), settingStr(run, "temperature"), settingStr(run, "think"), settingStr(run, "repeats"), run.Route, strings.Join(run.Variants, ", "))
	w("## Headline\n\n| Metric | Value |\n|---|---|")
	w("| Accuracy (excl. no_context) | %s (%d/%d) |", pct(s.Acc), s.K, s.N)
	w("| 95%% Wilson interval | %s – %s |", pct(s.Lo), pct(s.Hi))
	w("| Hallucination rate (unanswerable Qs) | %s |", pctP(s.Hallucination))
	w("| Over-refusal rate (answerable Qs) | %s |", pctP(s.OverRefusal))
	w("| Premise acceptance (false-premise Qs) | %s |", pctP(s.Premise))
	w("| Median latency | %s |", fsec(s.MedianLatency))
	w("| Mean tokens/s | %s |\n", f1(s.MeanTPS))
	w("## Accuracy by category\n\n| Category | Correct | n | Accuracy |\n|---|---|---|---|")
	for _, c := range s.CategoryOrder {
		g := s.ByCategory[c]
		w("| %s | %d | %d | %s |", c, g.K, g.N, pct(g.Acc()))
	}
	w("\n## Accuracy by prompt style\n\n| Variant | Correct | n | Accuracy |\n|---|---|---|---|")
	for _, c := range s.VariantOrder {
		g := s.ByVariant[c]
		w("| %s | %d | %d | %s |", c, g.K, g.N, pct(g.Acc()))
	}
	w("\n## Failure modes\n\n| Failure mode | Count | Meaning |\n|---|---|---|")
	for _, f := range s.FailureOrder {
		w("| %s | %d | %s |", f, s.FailureModes[f], failureHelp[f])
	}
	w("\n## All answers\n\n| Q | Variant | Rep | Verdict | Model's final answer | Expected | Scorer note |\n|---|---|---|---|---|---|---|")
	esc := func(x string) string { return strings.ReplaceAll(x, "|", "\\|") }
	for _, r := range run.Rows {
		v := r.FailureMode
		if r.Correct {
			v = "correct"
		}
		w("| %s | %s | %d | %s | %s | %s | %s |", r.QuestionID, r.Variant, r.Repeat+1, v, esc(oneLine(r.FinalAnswer, 160)), esc(r.ExpectedResponse), esc(r.ScoringDetail))
	}
	w("\n## Method\n\nEach question is asked with the store text in the prompt; the final answer (after any <think> block or FINAL ANSWER: marker) is scored by deterministic rules (numeric match, phrase match, yes/no, choice, list F1, abstention detection, premise correction). The `no_context` control is excluded from accuracy. Saved and exported by the grocery-llm-eval Go server v%s.", version)
	return b.String()
}

// ---------------------------------------------------------------- HTML export (printable)

var htmlTmpl = template.Must(template.New("r").Funcs(template.FuncMap{"pct": pct, "pctP": pctP, "fsec": fsec, "f1": f1, "inc": func(i int) int { return i + 1 }, "help": func(k string) string { return failureHelp[k] }, "line": func(s string) string { return oneLine(s, 200) }}).Parse(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Report {{.Run.Model}} {{.Run.ID}}</title>
<style>body{font-family:"IBM Plex Sans",system-ui,sans-serif;color:#161616;background:#fff;max-width:960px;margin:2em auto;padding:0 1em;line-height:1.5}h1,h2{color:#002d9c}table{border-collapse:collapse;width:100%;font-size:.9em;margin:.5em 0 1.5em}th,td{border:1px solid #e0e0e0;padding:.35em .5em;text-align:left;vertical-align:top}th{background:#f4f4f4}.ok{color:#198038}.bad{color:#da1e28}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6em}.tile{border:1px solid #e0e0e0;border-top:4px solid #0f62fe;padding:.6em;text-align:center}.tile b{font-size:1.4em;color:#002d9c;display:block}@media print{button{display:none}}</style></head>
<body><button onclick="window.print()">Print / save as PDF</button>
<h1>Grocery-Store Benchmark — {{.Run.Model}}</h1>{{if .Watermark}}<p style="color:#da1e28"><b>{{.Watermark}}</b></p>{{end}}
<p>Run {{.Run.ID}}, started {{.Run.StartedAt}}{{if not .Run.Finished}} (incomplete){{end}}. Prompt styles: {{range $i,$v := .Run.Variants}}{{if $i}}, {{end}}{{$v}}{{end}}. Connection: {{.Run.Route}}.</p>
<div class="tiles"><div class="tile"><b>{{pct .S.Acc}}</b>Accuracy ({{.S.K}}/{{.S.N}})</div><div class="tile"><b>{{pct .S.Lo}}–{{pct .S.Hi}}</b>95% interval</div><div class="tile"><b>{{pctP .S.Hallucination}}</b>Hallucination</div><div class="tile"><b>{{pctP .S.OverRefusal}}</b>Over-refusal</div><div class="tile"><b>{{pctP .S.Premise}}</b>Premise accepted</div><div class="tile"><b>{{fsec .S.MedianLatency}}</b>Median latency</div></div>
<h2>Accuracy by category</h2><table><tr><th>Category</th><th>Correct</th><th>n</th><th>Accuracy</th></tr>{{range .S.CategoryOrder}}{{$g := index $.S.ByCategory .}}<tr><td>{{.}}</td><td>{{$g.K}}</td><td>{{$g.N}}</td><td>{{pct $g.Acc}}</td></tr>{{end}}</table>
<h2>Accuracy by prompt style</h2><table><tr><th>Variant</th><th>Correct</th><th>n</th><th>Accuracy</th></tr>{{range .S.VariantOrder}}{{$g := index $.S.ByVariant .}}<tr><td>{{.}}</td><td>{{$g.K}}</td><td>{{$g.N}}</td><td>{{pct $g.Acc}}</td></tr>{{end}}</table>
<h2>Failure modes</h2><table><tr><th>Failure mode</th><th>Count</th><th>Meaning</th></tr>{{range .S.FailureOrder}}<tr><td>{{.}}</td><td>{{index $.S.FailureModes .}}</td><td>{{help .}}</td></tr>{{end}}</table>
<h2>All answers</h2><table><tr><th>Q</th><th>Style</th><th>Rep</th><th>Verdict</th><th>Final answer</th><th>Expected</th><th>Note</th></tr>{{range .Run.Rows}}<tr><td>{{.QuestionID}}</td><td>{{.Variant}}</td><td>{{inc .Repeat}}</td><td>{{if .Correct}}<span class="ok">correct</span>{{else}}<span class="bad">{{.FailureMode}}</span>{{end}}</td><td>{{line .FinalAnswer}}</td><td>{{.ExpectedResponse}}</td><td>{{.ScoringDetail}}</td></tr>{{end}}</table>
<p><small>Scored by deterministic rules; the no_context control is excluded from accuracy. grocery-llm-eval server v{{.Version}}.</small></p></body></html>`))

// ---------------------------------------------------------------- storage

func runPath(id string) string { return filepath.Join(*dataDir, "runs", id+".json") }

func loadRun(id string) (*Run, error) {
	if !safeID.MatchString(id) {
		return nil, fmt.Errorf("bad id")
	}
	b, err := os.ReadFile(runPath(id))
	if err != nil {
		return nil, err
	}
	var r Run
	return &r, json.Unmarshal(b, &r)
}

func saveRun(r *Run) error {
	if r.ID == "" || !safeID.MatchString(r.ID) {
		r.ID = time.Now().UTC().Format("2006-01-02T15-04-05") + "-srv"
	}
	r.SavedAt = time.Now().UTC().Format(time.RFC3339)
	if err := os.MkdirAll(filepath.Join(*dataDir, "runs"), 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(r, "", " ")
	return os.WriteFile(runPath(r.ID), b, 0o644)
}

func listRuns() []map[string]interface{} {
	out := []map[string]interface{}{}
	files, _ := filepath.Glob(filepath.Join(*dataDir, "runs", "*.json"))
	sort.Sort(sort.Reverse(sort.StringSlice(files)))
	for _, f := range files {
		id := strings.TrimSuffix(filepath.Base(f), ".json")
		if r, err := loadRun(id); err == nil {
			k := 0
			for _, row := range r.Rows {
				if row.Correct {
					k++
				}
			}
			out = append(out, map[string]interface{}{"id": r.ID, "model": r.Model, "started_at": r.StartedAt, "saved_at": r.SavedAt, "rows": len(r.Rows), "correct": k, "finished": r.Finished, "variants": r.Variants})
		}
	}
	return out
}

// ---------------------------------------------------------------- HTTP

func cors(h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		h(w, r)
	}
}

func writeJSON(w http.ResponseWriter, code int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func proxyOllama(w http.ResponseWriter, r *http.Request) {
	target := strings.TrimSuffix(*ollamaURL, "/") + strings.TrimPrefix(r.URL.Path, "/api/ollama")
	if r.URL.RawQuery != "" {
		target += "?" + r.URL.RawQuery
	}
	body, err := io.ReadAll(io.LimitReader(r.Body, 50<<20))
	if err != nil {
		writeJSON(w, 400, map[string]string{"error": err.Error()})
		return
	}
	req, err := http.NewRequestWithContext(r.Context(), r.Method, target, bytes.NewReader(body))
	if err != nil {
		writeJSON(w, 502, map[string]string{"error": err.Error()})
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := (&http.Client{Timeout: 15 * time.Minute}).Do(req)
	if err != nil {
		writeJSON(w, 502, map[string]string{"error": "cannot reach Ollama at " + *ollamaURL + ": " + err.Error()})
		return
	}
	defer resp.Body.Close()
	w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

func runsHandler(w http.ResponseWriter, r *http.Request) {
	rest := strings.TrimPrefix(r.URL.Path, "/api/runs")
	rest = strings.Trim(rest, "/")
	if rest == "" {
		switch r.Method {
		case http.MethodGet:
			writeJSON(w, 200, map[string]interface{}{"runs": listRuns()})
		case http.MethodPost:
			var run Run
			if err := json.NewDecoder(io.LimitReader(r.Body, 50<<20)).Decode(&run); err != nil {
				writeJSON(w, 400, map[string]string{"error": "invalid JSON: " + err.Error()})
				return
			}
			if err := saveRun(&run); err != nil {
				writeJSON(w, 500, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, 200, map[string]string{"id": run.ID, "saved_at": run.SavedAt})
		default:
			writeJSON(w, 405, map[string]string{"error": "method not allowed"})
		}
		return
	}
	parts := strings.SplitN(rest, "/", 2)
	id, _ := url.PathUnescape(parts[0])
	run, err := loadRun(id)
	if err != nil {
		writeJSON(w, 404, map[string]string{"error": "run not found"})
		return
	}
	if len(parts) == 1 {
		if r.Method == http.MethodDelete {
			os.Remove(runPath(id))
			writeJSON(w, 200, map[string]string{"deleted": id})
			return
		}
		writeJSON(w, 200, run)
		return
	}
	switch parts[1] {
	case "report.md":
		w.Header().Set("Content-Type", "text/markdown; charset=utf-8")
		w.Header().Set("Content-Disposition", fmt.Sprintf("inline; filename=report-%s.md", id))
		io.WriteString(w, trialWatermark()+runMarkdown(run))
	case "run.json":
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=run-%s.json", id))
		writeJSON(w, 200, run)
	case "results.csv":
		w.Header().Set("Content-Type", "text/csv; charset=utf-8")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=results-%s.csv", id))
		cw := csv.NewWriter(w)
		cw.Write([]string{"run_id", "model", "question_id", "variant", "repeat", "category", "question", "expected_response", "final_answer", "correct", "score", "failure_mode", "scoring_detail", "refused", "latency_s", "completion_tokens", "tokens_per_s", "done_reason", "error"})
		for _, x := range run.Rows {
			e := ""
			if x.Error != nil {
				e = *x.Error
			}
			cw.Write([]string{run.ID, run.Model, x.QuestionID, x.Variant, fmt.Sprint(x.Repeat), x.Category, x.Question, x.ExpectedResponse, oneLine(x.FinalAnswer, 2000), fmt.Sprint(x.Correct), fmt.Sprint(x.Score), x.FailureMode, x.ScoringDetail, fmt.Sprint(x.Refused), f1(x.LatencyS), fmt.Sprint(deref(x.CompletionTokens)), f1(x.TokensPerS), x.DoneReason, e})
		}
		cw.Flush()
	case "report.html":
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		var buf bytes.Buffer
		if err := htmlTmpl.Execute(&buf, map[string]interface{}{"Run": run, "S": summarize(run), "Version": version, "Watermark": strings.TrimSpace(trialWatermark())}); err != nil {
			writeJSON(w, 500, map[string]string{"error": err.Error()})
			return
		}
		w.Write(buf.Bytes())
	case "report.pdf":
		w.Header().Set("Content-Type", "application/pdf")
		w.Header().Set("Content-Disposition", fmt.Sprintf("inline; filename=report-%s.pdf", id))
		w.Write(runPDF(run))
	default:
		writeJSON(w, 404, map[string]string{"error": "unknown export; use report.md, run.json, results.csv, report.html or report.pdf"})
	}
}

func deref(p *int) int {
	if p == nil {
		return 0
	}
	return *p
}

func main() {
	flag.Parse()
	if *activate != "" {
		p, err := verifyLicense(*activate)
		if err != nil {
			log.Fatalf("activation failed: %v", err)
		}
		os.MkdirAll(*dataDir, 0o755)
		if err := os.WriteFile(licensePath(), []byte(strings.TrimSpace(*activate)+"\n"), 0o600); err != nil {
			log.Fatal(err)
		}
		fmt.Printf("Activated. Licensed to %s <%s>, %s plan, updates until %s. Saved to %s\n", p.Name, p.Email, p.Plan, p.Expires, licensePath())
		return
	}
	if st := currentLicense(); st.Licensed {
		log.Printf("licensed to %s <%s> (%s, updates until %s)", st.Payload.Name, st.Payload.Email, st.Payload.Plan, st.Payload.Expires)
	} else {
		log.Printf("TRIAL MODE (%s): starter questions + baseline style, watermarked exports. Activate with -activate <KEY> or in the lab page.", st.Reason)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", cors(func(w http.ResponseWriter, r *http.Request) {
		ollama := "unreachable"
		c := &http.Client{Timeout: 3 * time.Second}
		if resp, err := c.Get(strings.TrimSuffix(*ollamaURL, "/") + "/api/version"); err == nil {
			defer resp.Body.Close()
			var v struct{ Version string }
			json.NewDecoder(resp.Body).Decode(&v)
			ollama = "ok " + v.Version
		}
		writeJSON(w, 200, map[string]interface{}{"status": "ok", "version": version, "ollama": *ollamaURL, "ollama_status": ollama, "runs": len(listRuns()), "licensed": currentLicense().Licensed, "time": time.Now().UTC().Format(time.RFC3339)})
	}))
	mux.HandleFunc("/api/license", cors(licenseHandler))
	mux.HandleFunc("/api/ollama/", cors(proxyOllama))
	mux.HandleFunc("/api/runs", cors(runsHandler))
	mux.HandleFunc("/api/runs/", cors(runsHandler))
	if st, err := os.Stat(*webDir); err == nil && st.IsDir() {
		mux.Handle("/", http.FileServer(http.Dir(*webDir)))
	} else {
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			fmt.Fprintf(w, "grocery-llm-eval server v%s. web folder %q not found; API available under /api/.\n", version, *webDir)
		})
	}
	log.Printf("grocery-llm-eval server v%s listening on %s (Ollama: %s, web: %s, data: %s)", version, *addr, *ollamaURL, *webDir, *dataDir)
	log.Printf("open http://localhost%s/ for the tutorial and /lab.html for the live lab", strings.TrimPrefix(*addr, "0.0.0.0"))
	log.Fatal(http.ListenAndServe(*addr, mux))
}
