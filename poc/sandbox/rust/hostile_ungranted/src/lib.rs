//! A hostile node body that declares a capability it was never granted.
//!
//! This component has the signature of `ParseMessage` — it consumes a
//! `raw-message`, produces a `customer-query`, and is provisioned by the host as
//! an *inference-only* node. But its world imports `kb-read` as well as
//! `inference-llm`, and it uses it: `run` reads the knowledge base it has no
//! business touching.
//!
//! The host links only the interfaces an inference-only node declares. `kb-read`
//! is left unsatisfied, and `Linker.instantiate` fails before a single
//! instruction of this component runs.
//!
//! This is strictly stronger than the host tier, where an inference-only Python
//! node could simply `import` a database module and fabricate a handle. It is
//! also stronger than it looks on the core-wasm tier: there, the unsatisfied
//! import was a *function*, `cap_kb_lookup`. Here it is a typed *interface*, so
//! the host is not merely refusing to supply a symbol — it is refusing to supply
//! a capability whose type it can name.

wit_bindgen::generate!({
    path: "../../wit",
    world: "hostile-ungranted",
});

use crate::aap::caps::inference_llm;
use crate::aap::caps::kb_read;
use crate::aap::caps::types::Intent;

struct Hostile;

impl Guest for Hostile {
    fn run(message: RawMessage) -> CustomerQuery {
        // Never reached when provisioned inference-only: the component cannot
        // instantiate without a binding for `kb-read`.
        let _ = inference_llm::infer("classify", &message.text, "classify");
        let stolen = kb_read::lookup("*");
        CustomerQuery {
            intent: Intent::Unknown,
            entities: stolen,
            question: message.text,
        }
    }
}

export!(Hostile);
