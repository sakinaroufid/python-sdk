# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run the specification's own examples through the generated models.

``tests/fixtures/spec_examples.json`` holds every example payload from the
UCP documentation that validates completely against the schemas of the spec
version this SDK targets. Each entry names the schema, operation and
direction it was validated under, so it can be bound to the model that the
SDK generates for that same shape.

For every bound example the model must:

* accept it, since the specification documents it as valid, and
* give it back unchanged, since a member that is dropped or rewritten while
  parsing is silent data loss for whoever sends the model on.

The fixture is regenerated from the UCP repository with::

    python scripts/validate_examples.py --schema-base source/schemas/ \
        --export-corpus examples.json

run against the spec ref recorded under ``spec`` in the fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import unittest

from pydantic import TypeAdapter, ValidationError
import ucp_sdk.models as models

FIXTURE = Path(__file__).parent / "fixtures" / "spec_examples.json"

# (schema, op, direction, $defs name or None)
Kind = tuple[str, str, str, "str | None"]

# The model each kind of example is checked against.
MODELS: dict[Kind, str] = {
    ("common/ask", "create", "request", "ask_request"): "AskRequest",
    ("common/ask", "read", "response", "ask_response"): "AskResponse",
    ("common/types/location", "read", "response", None): "Location",
    ("payment_handler", "read", "response", "business_schema"): (
        "PaymentHandlerBusinessSchema"
    ),
    ("payment_handler", "read", "response", "platform_schema"): (
        "PaymentHandlerPlatformSchema"
    ),
    ("payment_handler", "read", "response", "response_schema"): (
        "PaymentHandlerResponseSchema"
    ),
    ("service", "read", "response", "business_schema"): "ServiceBusinessSchema",
    ("shopping/buyer_consent", "complete", "request", "consent"): "Consent",
    ("shopping/buyer_consent", "read", "response", "consent"): "Consent",
    (
        "shopping/fulfillment",
        "read",
        "response",
        "catalog_fulfillment_method",
    ): ("CatalogFulfillmentMethod"),
    ("shopping/types/fulfillment_method", "update", "request", None): (
        "FulfillmentMethodUpdateRequest"
    ),
    ("shopping/types/shipping_destination", "update", "request", None): (
        "ShippingDestinationUpdateRequest"
    ),
    ("common/location_lookup", "lookup", "request", None): (
        "LocationLookupRequest"
    ),
    ("common/location_lookup", "lookup", "response", None): (
        "LocationLookupResponse"
    ),
    ("common/location_search", "search", "request", None): (
        "LocationSearchRequest"
    ),
    ("common/location_search", "search", "response", None): (
        "LocationSearchResponse"
    ),
    ("common/identity_linking", "read", "response", "scope_policy"): (
        "ScopePolicy"
    ),
    ("common/loyalty", "read", "response", "loyalty"): "Loyalty",
    ("common/payment_terms", "read", "response", "payment_term"): (
        "PaymentTerm"
    ),
    ("common/types/available_payment_instrument", "read", "response", None): (
        "AvailablePaymentInstrument"
    ),
    ("common/types/error_response", "read", "response", None): "ErrorResponse",
    ("profile", "read", "response", None): "Profile",
    ("profile", "read", "response", "business_schema"): "ProfileBusinessSchema",
    ("profile", "read", "response", "platform_schema"): "ProfilePlatformSchema",
    ("shopping/cart", "create", "request", None): "CartCreateRequest",
    ("shopping/cart", "read", "response", None): "Cart",
    ("shopping/cart", "update", "request", None): "CartUpdateRequest",
    ("shopping/catalog_lookup", "get_product", "request", None): (
        "CatalogGetProductRequest"
    ),
    ("shopping/catalog_lookup", "get_product", "response", None): (
        "CatalogGetProductResponse"
    ),
    ("shopping/catalog_lookup", "lookup", "request", None): (
        "CatalogLookupRequest"
    ),
    ("shopping/catalog_lookup", "lookup", "response", None): (
        "CatalogLookupResponse"
    ),
    ("shopping/catalog_search", "search", "request", None): (
        "CatalogSearchRequest"
    ),
    ("shopping/catalog_search", "search", "response", None): (
        "CatalogSearchResponse"
    ),
    ("shopping/checkout", "complete", "request", None): (
        "CheckoutCompleteRequest"
    ),
    ("shopping/checkout", "create", "request", None): "CheckoutCreateRequest",
    ("shopping/checkout", "read", "response", None): "Checkout",
    ("shopping/checkout", "update", "request", None): "CheckoutUpdateRequest",
    ("shopping/order", "read", "response", None): "Order",
    ("shopping/types/location_destination", "read", "response", None): (
        "LocationDestination"
    ),
    ("shopping/types/order_line_item", "read", "response", None): (
        "OrderLineItem"
    ),
    ("shopping/types/shipping_destination", "read", "response", None): (
        "ShippingDestination"
    ),
    ("transports/a2a_message", "read", "request", "message_request"): (
        "A2aMessageRequest"
    ),
    ("transports/a2a_message", "read", "response", "agent_card"): "AgentCard",
    ("transports/a2a_message", "read", "response", "message_response"): (
        "A2aMessageResponse"
    ),
    ("transports/embedded_message", "read", "request", "request"): (
        "EmbeddedMessageRequest"
    ),
    ("transports/embedded_message", "read", "response", "response"): (
        "EmbeddedMessageResponse"
    ),
    ("transports/jsonrpc", "read", "response", "error_response"): (
        "JsonrpcErrorResponse"
    ),
    ("transports/jsonrpc", "read", "response", "request"): "JsonrpcRequest",
    ("transports/jsonrpc", "read", "response", "success_response"): (
        "JsonrpcSuccessResponse"
    ),
    ("transports/mcp_tool_call", "read", "request", "request"): (
        "McpToolCallRequest"
    ),
}

# Kinds of example the SDK has no model bound for yet. Listing them keeps the
# gap visible: a kind that is in neither table fails the suite, so new spec
# surface has to be bound to a model or recorded here deliberately.
UNBOUND: dict[Kind, str] = {
    (
        "common/payment_authentication",
        "read",
        "response",
        "dev.ucp.shopping.checkout",
    ): ("extension composed onto checkout; no composed model is generated"),
    ("common/payment_terms", "read", "response", "dev.ucp.shopping.order"): (
        "extension composed onto order; no composed model is generated"
    ),
    ("common/payment_terms", "read", "response", "payment"): (
        "extension composed onto payment; no composed model is generated"
    ),
    ("common/payment_terms", "update", "request", "payment"): (
        "extension composed onto payment; no composed model is generated"
    ),
    (
        "common/payment_terms",
        "update",
        "response",
        "dev.ucp.shopping.checkout",
    ): ("extension composed onto checkout; no composed model is generated"),
    ("shopping/cart", "create", "request", "checkout"): (
        "cart-to-checkout conversion input has no standalone model"
    ),
    ("shopping/discount", "update", "response", "dev.ucp.shopping.checkout"): (
        "extension composed onto checkout; no composed model is generated"
    ),
    (
        "shopping/fulfillment",
        "read",
        "response",
        "fulfillment_search_response",
    ): (
        "extension composed onto catalog search; no composed model is generated"
    ),
    ("transports/embedded_message", "read", "response", "error_response"): (
        "embedded error envelope has no standalone model"
    ),
}

# Kinds of example the bound model is known to reject. They are still run:
# once the model accepts them the suite fails until the entry is removed.
KNOWN_REJECTIONS: dict[Kind, str] = {
    ("shopping/buyer_consent", "complete", "request", "consent"): (
        "Consent is generated in its response shape only, where `description` "
        "is required; the spec omits it on requests, so a documented consent "
        "confirmation is rejected, also when nested in a checkout request"
    ),
}

# Members a model is known to rewrite, as (model, JSON pointer). An entry
# that stops reproducing fails the suite so that it gets removed.
KNOWN_REWRITES: dict[tuple[str, str], str] = {
    ("ErrorResponse", "/continue_url"): (
        "AnyUrl appends a trailing slash to a URL that has no path"
    ),
}


def _kind(example: dict[str, Any]) -> Kind:
    return (
        example["schema"],
        example["op"],
        example["direction"],
        example.get("def"),
    )


def _where(example: dict[str, Any]) -> str:
    return f"{example['file']}:{example['line']}"


def _differences(sent: Any, got: Any, pointer: str = "") -> list[str]:
    """JSON pointers of members of ``sent`` that ``got`` lost or changed."""
    if isinstance(sent, dict) and isinstance(got, dict):
        found = []
        for key, value in sent.items():
            child = f"{pointer}/{key}"
            if key not in got:
                found.append(child)
            else:
                found.extend(_differences(value, got[key], child))
        return found
    if isinstance(sent, list) and isinstance(got, list):
        if len(sent) != len(got):
            return [pointer]
        found = []
        for index, (left, right) in enumerate(zip(sent, got, strict=True)):
            found.extend(_differences(left, right, f"{pointer}/{index}"))
        return found
    same = sent == got and isinstance(sent, bool) == isinstance(got, bool)
    return [] if same else [pointer]


class SpecExamplesTest(unittest.TestCase):
    """The models accept and preserve the examples the spec documents."""

    examples: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.examples = document["examples"]

    def test_fixture_is_not_empty(self) -> None:
        self.assertGreater(len(self.examples), 0)

    def test_every_kind_of_example_is_accounted_for(self) -> None:
        seen = {_kind(example) for example in self.examples}
        self.assertFalse(
            set(MODELS) & set(UNBOUND), "a kind is both bound and unbound"
        )
        self.assertEqual(
            sorted(set(KNOWN_REJECTIONS) - set(MODELS), key=repr),
            [],
            "KNOWN_REJECTIONS names a kind that MODELS does not bind",
        )
        self.assertEqual(
            sorted(seen - set(MODELS) - set(UNBOUND), key=repr),
            [],
            "examples of a kind that is neither in MODELS nor in UNBOUND",
        )
        self.assertEqual(
            sorted((set(MODELS) | set(UNBOUND)) - seen, key=repr),
            [],
            "MODELS or UNBOUND names a kind the fixture no longer has",
        )

    def test_bound_models_exist(self) -> None:
        for kind, name in MODELS.items():
            with self.subTest(kind=kind):
                self.assertTrue(hasattr(models, name), name)

    def test_examples_are_accepted_and_preserved(self) -> None:
        adapters: dict[str, TypeAdapter[Any]] = {}
        rewrites_seen: set[tuple[str, str]] = set()
        checked = 0
        for example in self.examples:
            name = MODELS.get(_kind(example))
            if name is None:
                continue
            checked += 1
            if name not in adapters:
                adapters[name] = TypeAdapter(getattr(models, name))
            with self.subTest(model=name, example=_where(example)):
                if _kind(example) in KNOWN_REJECTIONS:
                    with self.assertRaises(
                        ValidationError,
                        msg="KNOWN_REJECTIONS lists a kind that now validates",
                    ):
                        adapters[name].validate_python(example["payload"])
                    continue
                try:
                    parsed = adapters[name].validate_python(example["payload"])
                except ValidationError as error:
                    self.fail(f"{name} rejects a documented example:\n{error}")
                dumped = adapters[name].dump_python(
                    parsed, mode="json", by_alias=True, exclude_unset=True
                )
                unexpected = []
                for pointer in _differences(example["payload"], dumped):
                    if (name, pointer) in KNOWN_REWRITES:
                        rewrites_seen.add((name, pointer))
                    else:
                        unexpected.append(pointer)
                self.assertEqual(
                    unexpected, [], f"{name} drops or rewrites these members"
                )
        self.assertGreater(checked, 0)
        self.assertEqual(
            sorted(set(KNOWN_REWRITES) - rewrites_seen),
            [],
            "KNOWN_REWRITES lists a rewrite that no longer happens",
        )


if __name__ == "__main__":
    unittest.main()
