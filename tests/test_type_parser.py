"""Tests for scripts/type_parser.py."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from type_parser import (
    ParseError,
    TApp,
    TList,
    TName,
    TString,
    TSum,
    TVariant,
    contains_untrusted,
    is_assignable,
    is_untrusted,
    parse_type,
    sum_roles,
    sum_variant_type,
    unparse,
)


class TestAtoms(unittest.TestCase):
    def test_bare_identifier(self):
        self.assertEqual(parse_type("CustomerQuery"), TName("CustomerQuery"))

    def test_hyphenated_identifier(self):
        self.assertEqual(parse_type("read-write"), TName("read-write"))

    def test_string_literal_atom(self):
        # Strings only appear inside generic args in practice, but the
        # atom grammar allows them anywhere.
        self.assertEqual(parse_type("'some-string'"), TString("some-string"))

    def test_rejects_empty(self):
        with self.assertRaises(ParseError):
            parse_type("")
        with self.assertRaises(ParseError):
            parse_type("   ")

    def test_rejects_unclosed_string(self):
        with self.assertRaises(ParseError):
            parse_type("DBHandle<'unterminated")

    def test_rejects_trailing_garbage(self):
        with self.assertRaises(ParseError):
            parse_type("CustomerQuery garbage")


class TestApplication(unittest.TestCase):
    def test_single_type_arg(self):
        self.assertEqual(
            parse_type("Untrusted<RawMessage>"),
            TApp("Untrusted", (TName("RawMessage"),)),
        )

    def test_mixed_args_string_and_ident(self):
        self.assertEqual(
            parse_type("DBHandle<'knowledge-base', read-write>"),
            TApp(
                "DBHandle",
                (TString("knowledge-base"), TName("read-write")),
            ),
        )

    def test_list_arg(self):
        self.assertEqual(
            parse_type("LLMClient<[respond, lookup]>"),
            TApp(
                "LLMClient",
                (TList((TName("respond"), TName("lookup"))),),
            ),
        )

    def test_empty_list_arg(self):
        self.assertEqual(
            parse_type("LLMClient<[]>"),
            TApp("LLMClient", (TList(()),)),
        )

    def test_nested_generics(self):
        self.assertEqual(
            parse_type("Outer<Inner<T>>"),
            TApp("Outer", (TApp("Inner", (TName("T"),)),)),
        )

    def test_string_with_internal_colon(self):
        # HTTPRoute<'platform:*'> — the colon must not be mistaken
        # for a variant separator because it is inside a string.
        self.assertEqual(
            parse_type("HTTPRoute<'platform:*'>"),
            TApp("HTTPRoute", (TString("platform:*"),)),
        )

    def test_rejects_generic_on_non_name(self):
        with self.assertRaises(ParseError):
            parse_type("'str'<X>")


class TestSumTypes(unittest.TestCase):
    def test_two_variants(self):
        t = parse_type("ok: AgentResponse | error: LLMError")
        self.assertEqual(
            t,
            TSum(
                (
                    TVariant("ok", TName("AgentResponse")),
                    TVariant("error", TName("LLMError")),
                )
            ),
        )

    def test_three_variants_real(self):
        t = parse_type(
            "ok: ModeratedQuery | violation: PolicyViolation | escalation: EscalationRequest"
        )
        self.assertIsInstance(t, TSum)
        self.assertEqual(sum_roles(t), ["ok", "violation", "escalation"])

    def test_sum_roles_on_non_sum(self):
        self.assertEqual(sum_roles(parse_type("CustomerQuery")), [])

    def test_sum_variant_type_lookup(self):
        t = parse_type("ok: AgentResponse | error: LLMError")
        self.assertEqual(sum_variant_type(t, "ok"), TName("AgentResponse"))
        self.assertEqual(sum_variant_type(t, "error"), TName("LLMError"))
        self.assertIsNone(sum_variant_type(t, "missing"))


class TestTrustPredicates(unittest.TestCase):
    def test_is_untrusted_positive(self):
        self.assertTrue(is_untrusted(parse_type("Untrusted<RawMessage>")))

    def test_is_untrusted_negative(self):
        self.assertFalse(is_untrusted(parse_type("RawMessage")))
        self.assertFalse(is_untrusted(parse_type("CustomerQuery")))

    def test_contains_untrusted_in_sum(self):
        t = parse_type("ok: Untrusted<X> | err: LLMError")
        self.assertTrue(contains_untrusted(t))

    def test_contains_untrusted_clean_sum(self):
        t = parse_type("ok: A | err: B")
        self.assertFalse(contains_untrusted(t))

    def test_contains_untrusted_bare(self):
        # is_untrusted only inspects the top level; nested Untrusted
        # inside generic args doesn't count as top-level untrusted.
        t = parse_type("Wrapper<Untrusted<X>>")
        self.assertFalse(contains_untrusted(t))


class TestCapabilitySubtyping(unittest.TestCase):
    def _assignable(self, a: str, b: str) -> bool:
        return is_assignable(parse_type(a), parse_type(b))

    def test_equal_types_are_assignable(self):
        self.assertTrue(self._assignable("CustomerQuery", "CustomerQuery"))
        self.assertTrue(self._assignable("LLMClient<[lookup]>", "LLMClient<[lookup]>"))

    def test_data_types_reject_inequality(self):
        self.assertFalse(self._assignable("TypeA", "TypeB"))

    def test_llm_wider_tool_set_is_assignable_to_narrower(self):
        self.assertTrue(self._assignable("LLMClient<[lookup, respond]>", "LLMClient<[lookup]>"))

    def test_llm_narrower_tool_set_is_not_assignable_to_wider(self):
        self.assertFalse(self._assignable("LLMClient<[lookup]>", "LLMClient<[lookup, respond]>"))

    def test_llm_inference_is_empty_tool_set(self):
        # Any LLMClient is at least inference; inference is assignable
        # only to another inference (or an equal empty-tool form).
        self.assertTrue(self._assignable("LLMClient<[lookup]>", "LLMClient<inference>"))
        self.assertFalse(self._assignable("LLMClient<inference>", "LLMClient<[lookup]>"))
        self.assertTrue(self._assignable("LLMClient<inference>", "LLMClient<inference>"))

    def test_db_read_write_is_assignable_to_read(self):
        self.assertTrue(self._assignable("DBHandle<'kb', read-write>", "DBHandle<'kb', read>"))

    def test_db_read_write_is_assignable_to_append(self):
        self.assertTrue(self._assignable("DBHandle<'kb', read-write>", "DBHandle<'kb', append>"))

    def test_db_read_is_not_assignable_to_read_write(self):
        self.assertFalse(self._assignable("DBHandle<'kb', read>", "DBHandle<'kb', read-write>"))

    def test_db_read_and_append_are_incomparable(self):
        self.assertFalse(self._assignable("DBHandle<'kb', read>", "DBHandle<'kb', append>"))
        self.assertFalse(self._assignable("DBHandle<'kb', append>", "DBHandle<'kb', read>"))

    def test_db_scope_must_match_exactly(self):
        self.assertFalse(self._assignable("DBHandle<'kb', read>", "DBHandle<'other', read>"))

    def test_other_generic_types_use_strict_equality(self):
        self.assertFalse(self._assignable("Foo<A>", "Foo<B>"))
        self.assertFalse(
            self._assignable("ResponseChannel<session-a>", "ResponseChannel<session-b>")
        )


class TestUnparseRoundtrip(unittest.TestCase):
    def test_roundtrip(self):
        cases = [
            "CustomerQuery",
            "Untrusted<RawMessage>",
            "DBHandle<'knowledge-base', read-write>",
            "LLMClient<[respond, lookup]>",
            "LLMClient<inference>",
            "HTTPRoute<'platform:*'>",
            "HTTPRequest<'POST', 'customer:message'>",
            "ok: AgentResponse | error: LLMError",
            "ok: ModeratedQuery | violation: PolicyViolation | escalation: EscalationRequest",
            "Outer<Inner<T>>",
            "LLMClient<[]>",
        ]
        for s in cases:
            with self.subTest(src=s):
                self.assertEqual(unparse(parse_type(s)), s)


if __name__ == "__main__":
    unittest.main()
