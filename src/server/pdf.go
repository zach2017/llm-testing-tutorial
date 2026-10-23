package main

// Minimal PDF writer (text only, Helvetica, automatic pagination). No external dependencies.
// Good enough for a readable, printable report; for fancy layouts use report.html and print to PDF.

import (
	"bytes"
	"fmt"
	"strings"
	"unicode"
)

type pdfDoc struct {
	pages   []*bytes.Buffer
	cur     *bytes.Buffer
	y       float64
	w, h    float64
	margin  float64
	bold    bool
	size    float64
	leading float64
}

func newPDF() *pdfDoc {
	d := &pdfDoc{w: 612, h: 792, margin: 54}
	d.newPage()
	return d
}

func (d *pdfDoc) newPage() {
	d.cur = &bytes.Buffer{}
	d.pages = append(d.pages, d.cur)
	d.y = d.h - d.margin
}

func pdfEscape(s string) string {
	var b strings.Builder
	for _, r := range s {
		switch {
		case r == '(' || r == ')' || r == '\\':
			b.WriteByte('\\')
			b.WriteRune(r)
		case r == '…':
			b.WriteString("...")
		case r == '–' || r == '—':
			b.WriteByte('-')
		case r == '’' || r == '‘':
			b.WriteByte('\'')
		case r == '“' || r == '”':
			b.WriteByte('"')
		case r < 32:
			b.WriteByte(' ')
		case r > 126:
			if r <= 255 {
				b.WriteString(fmt.Sprintf("\\%03o", r))
			} else if unicode.IsSpace(r) {
				b.WriteByte(' ')
			} else {
				b.WriteByte('?')
			}
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// approximate Helvetica average character width (fraction of font size)
func textWidth(s string, size float64) float64 { return float64(len(s)) * size * 0.5 }

func (d *pdfDoc) wrap(s string, size float64, width float64) []string {
	words := strings.Fields(s)
	if len(words) == 0 {
		return []string{""}
	}
	var lines []string
	cur := ""
	for _, w := range words {
		cand := w
		if cur != "" {
			cand = cur + " " + w
		}
		if textWidth(cand, size) > width && cur != "" {
			lines = append(lines, cur)
			cur = w
		} else {
			cur = cand
		}
	}
	return append(lines, cur)
}

func (d *pdfDoc) line(s string, size float64, bold bool, indent float64) {
	lead := size * 1.35
	for _, ln := range d.wrap(s, size, d.w-2*d.margin-indent) {
		if d.y-lead < d.margin {
			d.newPage()
		}
		d.y -= lead
		font := "/F1"
		if bold {
			font = "/F2"
		}
		fmt.Fprintf(d.cur, "BT %s %.1f Tf %.1f %.1f Td (%s) Tj ET\n", font, size, d.margin+indent, d.y, pdfEscape(ln))
	}
}

func (d *pdfDoc) gap(pts float64) {
	d.y -= pts
	if d.y < d.margin {
		d.newPage()
	}
}

func (d *pdfDoc) table(headers []string, rows [][]string, widths []float64, size float64) {
	// widths are fractions of the usable width
	usable := d.w - 2*d.margin
	xs := make([]float64, len(widths)+1)
	for i, f := range widths {
		xs[i+1] = xs[i] + f*usable
	}
	drawRow := func(cells []string, bold bool) {
		// wrap every cell, row height = tallest cell
		wrapped := make([][]string, len(cells))
		maxLines := 1
		for i, c := range cells {
			wrapped[i] = d.wrap(c, size, xs[i+1]-xs[i]-4)
			if len(wrapped[i]) > maxLines {
				maxLines = len(wrapped[i])
			}
		}
		lead := size * 1.3
		need := lead*float64(maxLines) + 4
		if d.y-need < d.margin {
			d.newPage()
			if !bold {
				drawRowHeader := headers
				_ = drawRowHeader
			}
		}
		top := d.y
		for i := range cells {
			for j, ln := range wrapped[i] {
				font := "/F1"
				if bold {
					font = "/F2"
				}
				fmt.Fprintf(d.cur, "BT %s %.1f Tf %.1f %.1f Td (%s) Tj ET\n", font, size, d.margin+xs[i]+2, top-lead*float64(j+1)+3, pdfEscape(ln))
			}
		}
		d.y = top - need
		// rule under the row
		fmt.Fprintf(d.cur, "0.85 G %.1f %.1f m %.1f %.1f l S 0 G\n", d.margin, d.y, d.margin+usable, d.y)
	}
	drawRow(headers, true)
	for _, r := range rows {
		drawRow(r, false)
	}
	d.gap(6)
}

func (d *pdfDoc) bytes() []byte {
	var out bytes.Buffer
	var offsets []int
	obj := func(body string) {
		offsets = append(offsets, out.Len())
		fmt.Fprintf(&out, "%d 0 obj\n%s\nendobj\n", len(offsets), body)
	}
	out.WriteString("%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
	// 1 catalog, 2 pages, 3 font regular, 4 font bold, then page/content pairs
	n := len(d.pages)
	kids := make([]string, n)
	for i := range d.pages {
		kids[i] = fmt.Sprintf("%d 0 R", 5+2*i)
	}
	obj("<< /Type /Catalog /Pages 2 0 R >>")
	obj(fmt.Sprintf("<< /Type /Pages /Kids [%s] /Count %d >>", strings.Join(kids, " "), n))
	obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
	obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
	for i, p := range d.pages {
		footer := fmt.Sprintf("BT /F1 8 Tf %.1f %.1f Td (grocery-llm-eval  -  page %d of %d) Tj ET\n", d.margin, d.margin/2, i+1, n)
		content := p.String() + footer
		obj(fmt.Sprintf("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>", d.w, d.h, 6+2*i))
		obj(fmt.Sprintf("<< /Length %d >>\nstream\n%sendstream", len(content), content))
	}
	xref := out.Len()
	fmt.Fprintf(&out, "xref\n0 %d\n0000000000 65535 f \n", len(offsets)+1)
	for _, o := range offsets {
		fmt.Fprintf(&out, "%010d 00000 n \n", o)
	}
	fmt.Fprintf(&out, "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n", len(offsets)+1, xref)
	return out.Bytes()
}

// runPDF renders the same content as the Markdown report.
func runPDF(run *Run) []byte {
	s := summarize(run)
	d := newPDF()
	d.line("Grocery-Store Benchmark - "+run.Model, 18, true, 0)
	if wm := trialWatermark(); wm != "" {
		d.line(strings.TrimSpace(wm), 9, true, 0)
	}
	status := ""
	if !run.Finished {
		status = " (incomplete)"
	}
	d.line(fmt.Sprintf("Run %s, started %s%s. Max tokens %s, temperature %s, thinking %s, repeats %s. Connection: %s. Prompt styles: %s.",
		run.ID, run.StartedAt, status, settingStr(run, "num_predict"), settingStr(run, "temperature"), settingStr(run, "think"), settingStr(run, "repeats"), run.Route, strings.Join(run.Variants, ", ")), 9, false, 0)
	d.gap(8)
	d.line("Headline", 13, true, 0)
	d.table([]string{"Metric", "Value"}, [][]string{
		{"Accuracy (excl. no_context)", fmt.Sprintf("%s (%d/%d)", pct(s.Acc), s.K, s.N)},
		{"95% Wilson interval", pct(s.Lo) + " - " + pct(s.Hi)},
		{"Hallucination rate (unanswerable Qs)", pctP(s.Hallucination)},
		{"Over-refusal rate (answerable Qs)", pctP(s.OverRefusal)},
		{"Premise acceptance (false-premise Qs)", pctP(s.Premise)},
		{"Median latency", fsec(s.MedianLatency)},
		{"Mean tokens/s", f1(s.MeanTPS)},
	}, []float64{0.55, 0.45}, 9)
	d.line("Accuracy by category", 13, true, 0)
	var rows [][]string
	for _, c := range s.CategoryOrder {
		g := s.ByCategory[c]
		rows = append(rows, []string{c, fmt.Sprint(g.K), fmt.Sprint(g.N), pct(g.Acc())})
	}
	d.table([]string{"Category", "Correct", "n", "Accuracy"}, rows, []float64{0.4, 0.2, 0.2, 0.2}, 9)
	d.line("Accuracy by prompt style", 13, true, 0)
	rows = nil
	for _, c := range s.VariantOrder {
		g := s.ByVariant[c]
		rows = append(rows, []string{c, fmt.Sprint(g.K), fmt.Sprint(g.N), pct(g.Acc())})
	}
	d.table([]string{"Variant", "Correct", "n", "Accuracy"}, rows, []float64{0.4, 0.2, 0.2, 0.2}, 9)
	d.line("Failure modes", 13, true, 0)
	rows = nil
	for _, f := range s.FailureOrder {
		rows = append(rows, []string{f, fmt.Sprint(s.FailureModes[f]), failureHelp[f]})
	}
	if len(rows) == 0 {
		rows = [][]string{{"none", "0", ""}}
	}
	d.table([]string{"Failure mode", "Count", "Meaning"}, rows, []float64{0.3, 0.12, 0.58}, 9)
	d.line("All answers", 13, true, 0)
	rows = nil
	for _, r := range run.Rows {
		v := r.FailureMode
		if r.Correct {
			v = "correct"
		}
		rows = append(rows, []string{r.QuestionID, r.Variant, v, oneLine(r.FinalAnswer, 220), oneLine(r.ExpectedResponse, 80)})
	}
	d.table([]string{"Q", "Style", "Verdict", "Model's final answer", "Expected"}, rows, []float64{0.07, 0.15, 0.15, 0.4, 0.23}, 8)
	d.line("Method: each question is asked with the store text in the prompt; the final answer (after any <think> block or FINAL ANSWER: marker) is scored by deterministic rules. The no_context control is excluded from accuracy. Exported by grocery-llm-eval server v"+version+".", 8, false, 0)
	return d.bytes()
}
