//! The library's `UpdateUserInfo`:
//!
//!   UpdateUserInfo : (ProfileUpdate) -> Receipt  with UserProfile<[fields]>
//!
//! Its world imports exactly `user-profile`. The password is not a field of it:
//! that is `credentials`, which no graph is granted and this world cannot name.

wit_bindgen::generate!({ path: "../../wit", world: "lib-update-user-info" });

use crate::aap::caps::user_profile;
use lib_common::{opt_text, order, receipt};

struct Node;

impl Guest for Node {
    fn run(_params: String, inputs: Vec<String>) -> Result<String, String> {
        let o = order(&inputs, "ProfileUpdate")?;
        receipt(user_profile::update(
            opt_text(&o, "first_name").as_deref(),
            opt_text(&o, "last_name").as_deref(),
            opt_text(&o, "street").as_deref(),
            opt_text(&o, "city").as_deref(),
        ))
    }
}

export!(Node);
