- [x] `Call` record and `NodeTrace.calls`, in encounter order with operation and index
- [x] `crossings` becomes a derived property (projection: forget operation and index, dedupe)
- [x] `to_dict`/`structural` exclude the journal from the compared form; schema gains optional `calls`
- [x] Tests: ordering and undeduplication, the projection identity, exclusion from the structural
      form, and schema-validity of the full form
- [x] Paper 2 §3.5 reports it as built, with the two limits (no values; host-tier-advisory) stated
- [x] Full suite green with the `poc` group, including the cross-tier structural-equality assertion
