//! S1's test guest. `burn` is CPU, `hog` is memory; neither touches a capability.

wit_bindgen::generate!({
    path: "../../wit",
    world: "spin",
});

struct Spin;

impl Guest for Spin {
    fn burn(n: u64) -> u64 {
        let mut x: u64 = 0x9E37_79B9_7F4A_7C15;
        let mut i: u64 = 0;
        while i < n {
            // xorshift: cheap, and data-dependent so the loop cannot be folded.
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            i += 1;
        }
        x
    }

    fn hog(mib: u32) -> u64 {
        let bytes = (mib as usize) * 1024 * 1024;
        let mut v: Vec<u8> = Vec::with_capacity(bytes);
        // Touch every page so the allocation is real.
        let mut i = 0;
        while i < bytes {
            v.push((i & 0xff) as u8);
            i += 1;
        }
        let total: u64 = v.iter().step_by(4096).map(|b| *b as u64).sum();
        total + v.len() as u64
    }
}

export!(Spin);
