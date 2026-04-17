ROOT := $(shell git rev-parse --show-toplevel)
DIST := $(ROOT)/dist

GRAPHS_SRC := $(filter-out graphs/schema.json,$(wildcard graphs/*.json))
GRAPHS_TXT := $(patsubst graphs/%.json,$(DIST)/graphs/%.graph,$(GRAPHS_SRC))
GRAPHS_SVG := $(patsubst graphs/%.json,$(DIST)/graphs/%.svg,$(GRAPHS_SRC))

DIAGRAMS_SRC := $(wildcard diagrams/*.typ)
DIAGRAMS_SVG := $(patsubst diagrams/%.typ,$(DIST)/diagrams/%.svg,$(DIAGRAMS_SRC))

.PHONY: build clean validate-graphs test

build: validate-graphs $(DIST)/proposal.pdf $(DIST)/proposal.md $(DIST)/proposal.html
	@echo "Build complete."

# Validate all graph JSON files: structural, type-aware, cross-graph.
# Depends on `test` so validator-logic changes are tested before use.
validate-graphs: test $(GRAPHS_SRC) scripts/validate-graphs.py scripts/graph_validator.py scripts/type_parser.py graphs/schema.json
	@python3 scripts/validate-graphs.py

# Run the unittest suite (type parser + graph validator).
test:
	@python3 -m unittest discover -s tests -t . 2>&1 | tail -3

# Generate pseudocode and diagram from canonical graph JSON
$(DIST)/graphs/%.graph $(DIST)/graphs/%.typ: graphs/%.json scripts/generate-graph.py | $(DIST)/graphs
	python3 scripts/generate-graph.py $<

# Compile diagram Typst to SVG
$(DIST)/graphs/%.svg: $(DIST)/graphs/%.typ
	typst compile $< $@ --format svg

# Hand-written illustrative diagrams
$(DIST)/diagrams/%.svg: diagrams/%.typ | $(DIST)/diagrams
	typst compile $< $@ --format svg

$(DIST)/proposal.pdf: proposal.typ citations.bib $(GRAPHS_TXT) $(GRAPHS_SVG) $(DIAGRAMS_SVG) | $(DIST)
	typst compile $< $@

$(DIST)/proposal.md: proposal.typ citations.bib $(GRAPHS_TXT) $(GRAPHS_SVG) $(DIAGRAMS_SVG) scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/clean-markdown.py | $(DIST)
	pandoc $< -f typst -t markdown --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		-o $@
	python3 scripts/clean-markdown.py $@

# Typst has experimental native HTML export (typst compile --format html --features html)
# but as of 0.13/0.14 it lacks CSS output and asset handling. Using pandoc for now.
$(DIST)/proposal.html: proposal.typ citations.bib $(GRAPHS_TXT) $(GRAPHS_SVG) $(DIAGRAMS_SVG) scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/proposal.css | $(DIST)
	pandoc $< -f typst -t html --standalone --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		--css=proposal.css \
		-o $@
	python3 scripts/clean-html.py $@
	cp scripts/proposal.css $(DIST)/

$(DIST):
	mkdir -p $@

$(DIST)/graphs: | $(DIST)
	mkdir -p $@

$(DIST)/diagrams: | $(DIST)
	mkdir -p $@

clean:
	rm -rf $(DIST)
