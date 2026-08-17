# Local LaTeX builds — no Overleaf, no compile quota.
#
#   make            build both PDFs
#   make conf       build conference/main.pdf
#   make diss       build dissertation/main.pdf
#   make watch-conf continuous rebuild on save (Ctrl-C to stop)
#   make figs       regenerate fig/*.pdf from fig/*.svg
#   make warnings   list undefined refs/citations and overfull boxes
#   make clean      remove build artefacts (keeps the PDFs)
#   make distclean  also remove the PDFs
#
# TeX Live was installed with `brew install texlive`, which does NOT put itself
# on PATH by default; hence TEXBIN below. `make` therefore works from any shell.
# SVG->PDF conversion needs librsvg (`brew install librsvg`).

TEXBIN  := /opt/homebrew/opt/texlive/bin
LATEXMK := $(TEXBIN)/latexmk
LMKOPTS := -pdf -synctex=1 -interaction=nonstopmode -file-line-error
SVGS    := $(wildcard */fig/*.svg)
PDFFIGS := $(SVGS:.svg=.pdf)

.PHONY: all conf diss watch-conf watch-diss figs warnings clean distclean

all: conf diss

conf: figs
	cd conference   && $(LATEXMK) $(LMKOPTS) main.tex

diss: figs
	cd dissertation && $(LATEXMK) $(LMKOPTS) main.tex

watch-conf: figs
	cd conference   && $(LATEXMK) $(LMKOPTS) -pvc main.tex

watch-diss: figs
	cd dissertation && $(LATEXMK) $(LMKOPTS) -pvc main.tex

figs: $(PDFFIGS)

%.pdf: %.svg
	rsvg-convert -f pdf -o $@ $<

warnings:
	@for d in conference dissertation; do \
	  echo "===== $$d"; \
	  grep -h "Reference .* undefined\|Citation .* undefined" $$d/main.log | sort -u || true; \
	  echo "-- overfull boxes:"; \
	  grep -h "Overfull \\\\hbox" $$d/main.log || echo "  none"; \
	done

clean:
	cd conference   && $(LATEXMK) -c main.tex
	cd dissertation && $(LATEXMK) -c main.tex

distclean:
	cd conference   && $(LATEXMK) -C main.tex
	cd dissertation && $(LATEXMK) -C main.tex
