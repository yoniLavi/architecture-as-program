ROOT := $(shell git rev-parse --show-toplevel)
DIST := $(ROOT)/dist

DIAGRAMS_SRC := $(wildcard diagrams/*.typ)
DIAGRAMS_SVG := $(patsubst diagrams/%.typ,$(DIST)/diagrams/%.svg,$(DIAGRAMS_SRC))

.PHONY: build clean

build: $(DIST)/proposal.pdf $(DIST)/proposal.md $(DIST)/proposal.html
	@echo "Build complete."

$(DIST)/diagrams/%.svg: diagrams/%.typ | $(DIST)/diagrams
	typst compile $< $@ --format svg

$(DIST)/proposal.pdf: proposal.typ citations.bib $(DIAGRAMS_SVG) | $(DIST)
	typst compile $< $@

$(DIST)/proposal.md: proposal.typ citations.bib $(DIAGRAMS_SVG) scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/clean-markdown.py | $(DIST)
	pandoc $< -f typst -t markdown --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		-o $@
	python3 scripts/clean-markdown.py $@

$(DIST)/proposal.html: proposal.typ citations.bib $(DIAGRAMS_SVG) scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/proposal.css | $(DIST)
	pandoc $< -f typst -t html --standalone --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		--css=proposal.css \
		-o $@
	cp scripts/proposal.css $(DIST)/

$(DIST):
	mkdir -p $@

$(DIST)/diagrams: | $(DIST)
	mkdir -p $@

clean:
	rm -rf $(DIST)
