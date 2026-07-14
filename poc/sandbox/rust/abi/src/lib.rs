//! Minimal, dependency-free ABI shared by every sandboxed node body.
//!
//! The boundary between the Python host and a WASM node is deliberately dumb:
//! bytes in linear memory, addressed by a packed `(ptr << 32) | len` i64. There
//! is no JSON parser and no external crate — every field-structured value is
//! framed with two ASCII separators so encode/decode is a `split`/`join`. Keeping
//! this trivial keeps the committed `.wasm` artifacts tiny and keeps the
//! confinement argument uncluttered by a serialisation runtime.
//!
//! Framing:
//!   * `FS` (unit separator, 0x1F) separates fields within a message.
//!   * `RS` (record separator, 0x1E) separates elements within a list field.
//!
//! Memory ownership: `alloc` leaks the buffer it returns. Each module instance is
//! short-lived (one node invocation, then dropped), so leaking is acceptable and
//! avoids a free protocol across the boundary. This is a PoC convenience, not a
//! production memory model.

/// Field separator within a message.
pub const FS: char = '\u{1f}';
/// Record separator between elements of a list field.
pub const RS: char = '\u{1e}';

/// Pack a pointer and length into the i64 the ABI passes across the boundary.
pub fn pack(ptr: i32, len: i32) -> i64 {
    (((ptr as u32 as u64) << 32) | (len as u32 as u64)) as i64
}

/// Split a packed i64 back into `(ptr, len)`.
pub fn unpack(v: i64) -> (i32, i32) {
    let v = v as u64;
    ((v >> 32) as i32, (v & 0xffff_ffff) as i32)
}

/// Allocate `size` bytes in linear memory and leak them; returns the pointer.
pub fn alloc_bytes(size: usize) -> *mut u8 {
    let mut buf = Vec::<u8>::with_capacity(size.max(1));
    let ptr = buf.as_mut_ptr();
    core::mem::forget(buf);
    ptr
}

/// Copy `len` bytes at `ptr` out of linear memory into an owned `String`.
///
/// # Safety
/// `ptr`/`len` must describe a valid, initialised UTF-8 region — they always do
/// here because both ends of the ABI only ever exchange UTF-8 text.
pub unsafe fn take_string(ptr: i32, len: i32) -> String {
    let bytes = core::slice::from_raw_parts(ptr as *const u8, len as usize).to_vec();
    String::from_utf8(bytes).unwrap_or_default()
}

/// Leak a string into linear memory and return its packed `(ptr, len)` — the
/// standard way a node returns its result, and the way the host writes a host
/// function's result back for the module to read.
pub fn leak_str(s: &str) -> i64 {
    let bytes = s.as_bytes();
    let ptr = alloc_bytes(bytes.len());
    unsafe { core::ptr::copy_nonoverlapping(bytes.as_ptr(), ptr, bytes.len()) };
    pack(ptr as i32, bytes.len() as i32)
}

/// Emit the exports every module must provide: `alloc`, used by the host to
/// place inputs and host-function results into the module's linear memory.
#[macro_export]
macro_rules! abi_exports {
    () => {
        #[no_mangle]
        pub extern "C" fn alloc(size: i32) -> i32 {
            $crate::alloc_bytes(size as usize) as i32
        }
    };
}
