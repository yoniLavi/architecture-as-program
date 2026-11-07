You are implementing the body of one node of a signal graph that carries out a banking task for a user. The body is a Rust crate compiled to a WebAssembly component. The target is `wasm32-unknown-unknown` with wit-bindgen 0.59 and no WASI adapter.

## The node

```
<<signature>>
```

What it does, in the words of the architect who designed the graph:

> <<role>>

Its inputs, in order, each as a JSON value:

<<inputs>>

It must return one JSON object with exactly these fields:

<<output>>

The node's `with` clause is its entire authority. It grants exactly these interfaces:

<<granted>>

## The component's boundary

The component must export exactly this function:

```wit
export run: func(params: string, inputs: list<string>) -> result<string, string>;
```

`inputs` holds one JSON string per input above, in order. `params` is a JSON object holding the node's name, its `role` and its output `fields`. Return `Ok` with the output object as a JSON string, or `Err` with a short reason if the node cannot do its job on these inputs.

## What to return

Either the body, or a request for authority.

**The body.** Two files, each in its own fenced code block, in this order:

1. `wit/world.wit`, in a ```wit block. It declares `package gen:node;` and one world named `node`, containing an `import` for each interface the body calls and the export above. Name interfaces in full, such as `import aap:caps/payments@0.1.0;`.
2. `src/lib.rs`, in a ```rust block: the complete source of the crate.

**A request for authority.** If the node cannot do what its role says with the interfaces it is granted, do not write the body. Reply with one JSON object and nothing else:

```json
{"escalate": {"capability": "<the capability the node needs, as a type such as Payments<['<payee>'], '<cap>'>>", "because": "<why the role needs it, in a sentence>"}}
```

The architect decides on a request. If it is granted, the graph is changed and reviewed again before anything runs, and you are asked again with the new grant.

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
    fn run(params: String, inputs: Vec<String>) -> Result<String, String> {
        todo!()
    }
}

export!(Node);
```

How wit-bindgen names things: an imported interface such as `aap:caps/payments` is the module `crate::aap::caps::payments`. Kebab-case WIT names become snake_case functions and fields. A WIT `string` parameter of an imported function is `&str` in Rust; a returned `string` is `String`; `list<T>` is `Vec<T>`; `option<T>` is `Option<T>`; `result<T, E>` is `Result<T, E>`.

## The `aap:caps` WIT package

Present in the crate at `wit/deps/caps/`. The general interfaces:

```wit
<<package>>
```

The banking interfaces, in the same package:

```wit
<<banking>>
```
