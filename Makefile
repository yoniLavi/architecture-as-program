ROOT := $(shell git rev-parse --show-toplevel)
DIST := $(ROOT)/dist

.PHONY: build clean

build: $(DIST)/proposal.pdf $(DIST)/proposal.md
	@echo "Build complete."

$(DIST)/proposal.pdf: proposal.typ citations.bib | $(DIST)
	typst compile $< $@

$(DIST)/proposal.md: proposal.typ citations.bib scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/clean-markdown.py | $(DIST)
	pandoc $< -f typst -t markdown --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		-o $@
	python3 scripts/clean-markdown.py $@

$(DIST):
	mkdir -p $@

clean:
	rm -rf $(DIST)
