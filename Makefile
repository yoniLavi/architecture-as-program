ROOT := $(shell git rev-parse --show-toplevel)
DIST := $(ROOT)/dist
PY   := uv run python3

GRAPHS_SRC := $(filter-out graphs/schema.json,$(wildcard graphs/*.json))
GRAPHS_TXT := $(patsubst graphs/%.json,$(DIST)/graphs/%.graph,$(GRAPHS_SRC))
GRAPHS_SVG := $(patsubst graphs/%.json,$(DIST)/graphs/%.svg,$(GRAPHS_SRC))

DIAGRAMS_SRC := $(wildcard diagrams/*.typ)
DIAGRAMS_SVG := $(patsubst diagrams/%.typ,$(DIST)/diagrams/%.svg,$(DIAGRAMS_SRC))

.PHONY: build clean validate-graphs test wasm

RUST_DIR    := $(ROOT)/poc/sandbox/rust
WASM_OUT    := $(ROOT)/poc/sandbox/wasm
# NOT wasm32-wasip1/wasip2: those link std against WASI, so the artifact would
# import fd_write/environ_get (wasip1) or wasi:cli/* (wasip2) even when it never
# uses them. Building for unknown-unknown and converting to a component with no
# WASI adapter leaves an import set containing only the node's capability
# interfaces — which is the property the component tier exists to demonstrate.
WASM_TARGET := wasm32-unknown-unknown
WASM_MODULES := node_parse_message node_generate_response hostile_ambient hostile_ungranted

build: validate-graphs $(DIST)/proposal.pdf $(DIST)/proposal.md $(DIST)/proposal.html $(DIST)/grammar.md
	@echo "Build complete."

# Grammar card — built from scripts/type_parser.py and the canonical
# graph JSONs so that the documented grammar and subtype rules cannot
# drift from the implementation without failing the build.
$(DIST)/grammar.md: scripts/emit-grammar.py scripts/type_parser.py $(GRAPHS_SRC) | $(DIST)
	$(PY) scripts/emit-grammar.py

# Validate all graph JSON files: structural, type-aware, cross-graph.
# Depends on `test` so validator-logic changes are tested before use.
validate-graphs: test $(GRAPHS_SRC) scripts/validate-graphs.py scripts/graph_validator.py scripts/type_parser.py graphs/schema.json
	@$(PY) scripts/validate-graphs.py

# Run the test suite (type parser + graph validator) via pytest.
test:
	@uv run pytest

# Build the component-tier WASM node artifacts and copy them into
# poc/sandbox/wasm/ (which is committed).
#
# Two steps, and the second is the interesting one:
#   1. cargo builds each node crate to a *core* module. wit_bindgen::generate!
#      reads poc/sandbox/wit/caps.wit and emits the typed bindings, plus a
#      `component-type` custom section describing the crate's world.
#   2. `wasm-tools component new` reads that section and wraps the core module
#      into a *component* whose imports and exports are the WIT interfaces. No
#      `--adapt` flag is passed: no WASI adapter is linked, so the component
#      imports nothing but its declared capability interfaces.
#
# Requires a Rust toolchain with the wasm32-unknown-unknown target
# (`rustup target add wasm32-unknown-unknown`) and wasm-tools
# (`brew install wasm-tools` / `cargo install wasm-tools`). This is NOT part of
# `make build` or the pre-commit hooks — the committed artifacts let the sandbox
# tests run without either toolchain. Rebuild only when the Rust sources or the
# WIT change.
wasm:
	cargo build --manifest-path $(RUST_DIR)/Cargo.toml --release --target $(WASM_TARGET)
	@mkdir -p $(WASM_OUT)
	@for m in $(WASM_MODULES); do \
		wasm-tools component new \
			$(RUST_DIR)/target/$(WASM_TARGET)/release/$$m.wasm \
			-o $(WASM_OUT)/$$m.wasm ; \
		echo "  wrote poc/sandbox/wasm/$$m.wasm (component)" ; \
	done

# Generate pseudocode and diagram from canonical graph JSON
$(DIST)/graphs/%.graph $(DIST)/graphs/%.typ: graphs/%.json scripts/generate-graph.py | $(DIST)/graphs
	$(PY) scripts/generate-graph.py $<

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
	$(PY) scripts/clean-markdown.py $@

# Typst has experimental native HTML export (typst compile --format html --features html)
# but as of 0.13/0.14 it lacks CSS output and asset handling. Using pandoc for now.
$(DIST)/proposal.html: proposal.typ citations.bib $(GRAPHS_TXT) $(GRAPHS_SVG) $(DIAGRAMS_SVG) scripts/resolve-crossrefs.lua scripts/ieee.csl scripts/proposal.css | $(DIST)
	pandoc $< -f typst -t html --standalone --wrap=none \
		--lua-filter=scripts/resolve-crossrefs.lua \
		--citeproc --bibliography=citations.bib --csl=scripts/ieee.csl \
		--css=proposal.css \
		-o $@
	$(PY) scripts/clean-html.py $@
	cp scripts/proposal.css $(DIST)/

$(DIST):
	mkdir -p $@

$(DIST)/graphs: | $(DIST)
	mkdir -p $@

$(DIST)/diagrams: | $(DIST)
	mkdir -p $@

clean:
	rm -rf $(DIST)
