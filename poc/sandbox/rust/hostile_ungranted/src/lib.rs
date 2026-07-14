//! A hostile node body that declares a capability import it was never granted.
//!
//! It imports `cap_kb_lookup` — the read-only knowledge-base handle. When the
//! host instantiates this module as an *inference-only* node (whose grant links
//! only `cap_infer`), `cap_kb_lookup` is not in the import table the host
//! provides, and instantiation fails before a single instruction runs.
//!
//! This is strictly stronger than the host tier, where an inference-only Python
//! node could still `import` and fabricate a database handle: here the capability
//! is absent, not merely unexposed. The same mechanism covers both "cannot call a
//! host function it was not linked with" and "an inference-only node has no tool
//! import at all".

use abi::{leak_str, take_string, unpack};

abi::abi_exports!();

#[link(wasm_import_module = "cap")]
extern "C" {
    fn cap_kb_lookup(ptr: i32, len: i32) -> i64;
}

#[no_mangle]
pub extern "C" fn run(_ptr: i32, _len: i32) -> i64 {
    // Never reached when provisioned inference-only: the module cannot instantiate
    // without a binding for `cap_kb_lookup`.
    let query = "*";
    let packed = unsafe { cap_kb_lookup(query.as_ptr() as i32, query.len() as i32) };
    let (p, l) = unpack(packed);
    let hits = unsafe { take_string(p, l) };
    leak_str(&format!("ungranted lookup returned: {hits}"))
}
