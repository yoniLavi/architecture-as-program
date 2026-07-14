//! A deliberately hostile node body that tries to reach ambient authority.
//!
//! It imports NO capability host functions. Under the sandbox tier (empty WASI:
//! no preopens, no sockets, no env, no clock) every attempt below fails, because
//! the authority is simply absent. The parallel host-tier attacks (ordinary
//! Python, in the test suite) succeed — that contrast is the whole point of the
//! hostile-node suite, and it is recorded in tests rather than asserted in prose.
//!
//! Each export returns `yes FS <detail>` if the escape succeeded or
//! `no FS <detail>` if it was denied.

use abi::{leak_str, FS};

abi::abi_exports!();

fn verdict(escaped: bool, detail: &str) -> i64 {
    let tag = if escaped { "yes" } else { "no" };
    leak_str(&format!("{tag}{FS}{detail}"))
}

/// Attempt to read a file outside any grant.
#[no_mangle]
pub extern "C" fn escape_fs() -> i64 {
    match std::fs::read_to_string("/etc/hostname") {
        Ok(contents) => verdict(true, &format!("read /etc/hostname: {contents:?}")),
        Err(e) => verdict(false, &format!("filesystem denied: {e}")),
    }
}

/// Attempt to open a network connection.
#[no_mangle]
pub extern "C" fn escape_net() -> i64 {
    match std::net::TcpStream::connect("127.0.0.1:9") {
        Ok(_) => verdict(true, "opened a TCP socket"),
        Err(e) => verdict(false, &format!("network denied: {e}")),
    }
}

/// Attempt to read an environment variable.
#[no_mangle]
pub extern "C" fn escape_env() -> i64 {
    match std::env::var("SANDBOX_SECRET") {
        Ok(v) => verdict(true, &format!("read SANDBOX_SECRET: {v:?}")),
        Err(e) => verdict(false, &format!("environment denied: {e}")),
    }
}
