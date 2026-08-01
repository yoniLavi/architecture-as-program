//! A hostile node body granted exactly a clock — and nothing else.
//!
//! `hostile_ambient` establishes that a component granted *nothing* can reach
//! nothing. This crate asks the sharper question the clock grant raises: does
//! holding one deliberately-granted WASI interface reopen the ambient world?
//!
//! It does not, and the mechanism is worth being precise about. The clock import
//! is a typed interface the host satisfies explicitly — it is not a WASI
//! *adapter*, and linking it brings no `fd_write`, no `sock_*`, no `path_open`
//! along. `std`'s filesystem and network backends remain absent on
//! `wasm32-unknown-unknown`, so the escapes below fail with `Unsupported`: not
//! denied at a gate, but with no gate to be denied at. The grant bought exactly
//! the authority it names, which `read-clock` proves is live.

wit_bindgen::generate!({
    path: "../../wit",
    world: "hostile-clocked",
    // See node_heartbeat: bindings for the foreign wasi:clocks package need an
    // explicit opt-in.
    generate_all,
});

use crate::wasi::clocks::wall_clock;

fn verdict(escaped: bool, detail: String) -> EscapeVerdict {
    EscapeVerdict { escaped, detail }
}

struct Hostile;

impl Guest for Hostile {
    /// The granted authority, exercised: the clock is live, not decorative.
    fn read_clock() -> u64 {
        wall_clock::now().seconds
    }

    /// Attempt to read a file while holding only a clock.
    fn escape_fs() -> EscapeVerdict {
        match std::fs::read_to_string("/etc/hostname") {
            Ok(contents) => verdict(true, format!("read /etc/hostname: {contents:?}")),
            Err(e) => verdict(false, format!("filesystem denied: {e}")),
        }
    }

    /// Attempt to open a network connection while holding only a clock.
    fn escape_net() -> EscapeVerdict {
        match std::net::TcpStream::connect("127.0.0.1:9") {
            Ok(_) => verdict(true, "opened a TCP socket".to_string()),
            Err(e) => verdict(false, format!("network denied: {e}")),
        }
    }
}

export!(Hostile);
