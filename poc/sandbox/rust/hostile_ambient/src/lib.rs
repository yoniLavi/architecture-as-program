//! A deliberately hostile node body that reaches for ambient authority.
//!
//! Its world (`hostile-ambient` in `wit/caps.wit`) imports **nothing**. The
//! component's import set is therefore empty, and the test suite asserts exactly
//! that. This is the component tier's strengthened form of "no ambient
//! authority", and it is worth being precise about how it differs from the tier
//! it replaces:
//!
//!   * On the **core-wasm tier**, this module was built for `wasm32-wasip1`. Its
//!     import table *did* contain `fd_write`, `environ_get`, `path_open` and the
//!     rest. Those imports were satisfied by an empty `WasiConfig` — no preopens,
//!     no env, no clock — so the calls below failed for lack of anything behind
//!     them. Confinement was a property of how the host configured the runtime.
//!
//!   * On the **component tier**, built for `wasm32-unknown-unknown` and
//!     converted with no WASI adapter, those imports do not exist. `std`'s
//!     filesystem, network and environment backends are absent on this target, so
//!     the calls below fail with `Unsupported` — not denied at a gate, but with
//!     no gate to be denied at. Confinement is a property of the artifact.
//!
//! The observable outcome is the same (every escape fails), which is the point:
//! the port strengthened the mechanism without weakening the result. Each export
//! returns an `escape-verdict` — `escaped: true` if the escape succeeded.

wit_bindgen::generate!({
    path: "../../wit",
    world: "hostile-ambient",
});

fn verdict(escaped: bool, detail: String) -> EscapeVerdict {
    EscapeVerdict { escaped, detail }
}

struct Hostile;

impl Guest for Hostile {
    /// Attempt to read a file outside any grant.
    fn escape_fs() -> EscapeVerdict {
        match std::fs::read_to_string("/etc/hostname") {
            Ok(contents) => verdict(true, format!("read /etc/hostname: {contents:?}")),
            Err(e) => verdict(false, format!("filesystem denied: {e}")),
        }
    }

    /// Attempt to open a network connection.
    fn escape_net() -> EscapeVerdict {
        match std::net::TcpStream::connect("127.0.0.1:9") {
            Ok(_) => verdict(true, "opened a TCP socket".to_string()),
            Err(e) => verdict(false, format!("network denied: {e}")),
        }
    }

    /// Attempt to read an environment variable.
    fn escape_env() -> EscapeVerdict {
        match std::env::var("SANDBOX_SECRET") {
            Ok(v) => verdict(true, format!("read SANDBOX_SECRET: {v:?}")),
            Err(e) => verdict(false, format!("environment denied: {e}")),
        }
    }
}

export!(Hostile);
