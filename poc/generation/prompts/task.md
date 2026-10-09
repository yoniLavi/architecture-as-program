You are implementing the body of one node of a signal graph, as a Rust crate compiled to a WebAssembly component. The target is `wasm32-unknown-unknown` with wit-bindgen 0.59 and no WASI adapter.

## The node

```
<<signature>>
```

<<contract>>

The node's `with` clause is its entire authority. It grants exactly these interfaces:

<<granted>>

The component must export exactly this function:

```wit
<<export>>
```

## What to return

Return two files, each in its own fenced code block, in this order:

1. `wit/world.wit`, in a ```wit block. It declares `package gen:node;` and one world named `node`, containing the `use` of the types the export names, an `import` for each interface the body calls, and the export above. Name interfaces in full: `import aap:caps/inference-llm@0.1.0;`, `use aap:caps/types@0.1.0.{raw-message};`.
2. `src/lib.rs`, in a ```rust block: the complete source of the crate.

Anything outside those two blocks is ignored.

## The crate you are completing

`Cargo.toml` is fixed, and you cannot add dependencies:

```toml
<<cargo>>
```

`src/lib.rs` starts from this skeleton:

```rust
wit_bindgen::generate!({
    path: "wit",
    world: "node",
    generate_all,
});

struct Node;

impl Guest for Node {
    // fn run(...) -> ... { ... }
}

export!(Node);
```

How wit-bindgen names things: a type named in your world's `use` is generated at the crate root; any other type of the package is at `crate::aap::caps::types::`. An imported interface such as `aap:caps/kb-read` is the module `crate::aap::caps::kb_read`. Kebab-case WIT names become CamelCase types and variant cases, and snake_case functions and fields. A WIT `string` parameter of an imported function is `&str` in Rust; a returned `string` is `String`; `list<T>` is `Vec<T>`; `option<T>` is `Option<T>`; `result<T, E>` is `Result<T, E>`.

## The Rust types your signature names

As wit-bindgen generates them:

```rust
<<types>>
```

## The `aap:caps` WIT package

Present in the crate at `wit/deps/caps/caps.wit`:

```wit
<<package>>
```

## The `wasi:clocks` WIT package

Present in the crate at `wit/deps/clocks/wall-clock.wit`:

```wit
<<clocks>>
```
