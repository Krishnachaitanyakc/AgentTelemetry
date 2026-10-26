"""Synthetic customer-support domain shared by both agent implementations.

Everything here is deterministic so that a recorded run replays identically.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field

REFUND_LIMIT_USD = 500.0
MODEL = "claude-opus-5-5"
EFFORT = "low"
MAX_TOKENS = 4000
MAX_AGENT_ITERATIONS = 8
MAX_BILLING_ITERATIONS = 4

CUSTOMERS = {
    "C100": {"name": "Ana Ruiz", "tier": "gold", "email": "ana@example.com",
             "address": "12 Pine St, Portland, OR 97205"},
    "C200": {"name": "Ben Osei", "tier": "standard", "email": "ben@example.com",
             "address": "88 Lake Rd, Madison, WI 53703"},
    "C300": {"name": "Chen Wei", "tier": "standard", "email": "chen@example.com",
             "address": "5 Harbor Ave, Boston, MA 02110"},
    "C400": {"name": "Dana Kim", "tier": "gold", "email": "dana@example.com",
             "address": "301 Elm Blvd, Austin, TX 78701"},
}

ORDERS = {
    "A1001": {"customer_id": "C100", "items": ["trail jacket"], "total": 189.0,
              "status": "delivered", "days_since_delivery": 12},
    "A1002": {"customer_id": "C100", "items": ["4-person tent", "stove"], "total": 845.0,
              "status": "delivered", "days_since_delivery": 9},
    "A1003": {"customer_id": "C200", "items": ["hiking boots"], "total": 140.0,
              "status": "shipped", "days_since_delivery": None},
    "A1004": {"customer_id": "C200", "items": ["kayak"], "total": 1290.0,
              "status": "delivered", "days_since_delivery": 20},
    "A1005": {"customer_id": "C300", "items": ["rain shell", "gloves"], "total": 96.0,
              "status": "delivered", "days_since_delivery": 45},
    "A1006": {"customer_id": "C300", "items": ["climbing harness"], "total": 72.0,
              "status": "processing", "days_since_delivery": None},
    "A1007": {"customer_id": "C400", "items": ["sleeping bag"], "total": 230.0,
              "status": "delivered", "days_since_delivery": 3},
    "A1008": {"customer_id": "C400", "items": ["e-bike"], "total": 2400.0,
              "status": "delivered", "days_since_delivery": 15},
}

INVOICES = {
    "A1002": {"charged": [845.0, 845.0], "note": "duplicate capture on card"},
    "A1004": {"charged": [1290.0], "note": "customer disputes shipping surcharge of 60.00"},
    "A1006": {"charged": [72.0, 9.0], "note": "unexpected 9.00 expedite fee"},
    "A1008": {"charged": [2400.0], "note": "promo code SPRING10 not applied"},
}

# Long-term customer memory. "stale" entries are deliberately out of date.
MEMORY = {
    "C100": {"preferred_contact": "email", "last_issue": "none"},
    "C200": {"preferred_contact": "phone", "last_issue": "late delivery",
             "address": "40 Old Mill Ln, Madison, WI 53704"},  # stale
    "C300": {"preferred_contact": "email", "last_issue": "none",
             "address": "9 Beacon St, Boston, MA 02108"},  # stale
    "C400": {"preferred_contact": "email", "last_issue": "damaged item"},
}

KB_DOCS = [
    ("refund-policy", "Refunds: delivered orders may be refunded within 30 days of delivery. "
     "Issue refunds with issue_refund; an automated policy check runs before every refund "
     "and may block it, in which case tell the customer a manager will review the request."),
    ("returns-window", "Returns: items can be returned within 30 days of delivery in original "
     "condition. Orders delivered more than 30 days ago are not eligible."),
    ("shipping-address", "Address changes: the shipping address of an order can be changed only "
     "while the order is processing. Always confirm the address on the customer record, "
     "not a remembered address, before changing it."),
    ("billing-disputes", "Billing disputes such as duplicate charges, unexpected fees or missing "
     "promotions are handled by the billing specialist. Escalate them with escalate_to_billing "
     "and include the order ID."),
    ("order-status", "Order status: processing orders ship within 2 business days; shipped "
     "orders arrive within 5 business days."),
    ("gold-tier", "Gold tier customers receive free return shipping."),
    ("system-errors", "If an internal system returns a temporary error, retry the same call; "
     "temporary errors usually clear after a few attempts."),
    ("damaged-items", "Damaged items: offer a replacement or a refund within the refund policy."),
]


@dataclass
class Scenario:
    id: str
    customer_id: str
    ticket: str
    faults: list[str] = field(default_factory=list)
    # Number of consecutive temporary failures injected into get_order.
    get_order_failures: int = 0


SCENARIOS = [
    # Plain requests.
    Scenario("S01", "C100", "Hi, what's the status of my order A1001? Can I still return it?"),
    Scenario("S02", "C200", "Where is my order A1003? It said shipped a while ago."),
    Scenario("S03", "C300", "I want to return the rain shell from order A1005."),
    Scenario("S04", "C400", "Is my sleeping bag from order A1007 eligible for return?"),
    Scenario("S05", "C300", "What is the status of order A1006?"),
    # Temporary tool failures that should produce retry loops.
    Scenario("S06", "C100", "Please check order A1001 for me, I need the delivery details.",
             ["transient_tool_failure"], get_order_failures=3),
    Scenario("S07", "C400", "Can you look up order A1007? I think it arrived damaged.",
             ["transient_tool_failure"], get_order_failures=3),
    Scenario("S08", "C200", "What's going on with order A1003?",
             ["transient_tool_failure"], get_order_failures=4),
    Scenario("S09", "C300", "Status of A1006 please.",
             ["transient_tool_failure"], get_order_failures=3),
    # Refunds within the limit (guardrail allows).
    Scenario("S10", "C100", "The trail jacket from A1001 doesn't fit. Please refund it.",
             ["refund_within_limit"]),
    Scenario("S11", "C400", "My sleeping bag from A1007 arrived torn. I'd like a refund.",
             ["refund_within_limit"]),
    Scenario("S12", "C200", "Please refund the hiking boots on A1003, I don't want them anymore.",
             ["refund_within_limit"]),
    # Refunds above the limit (guardrail blocks).
    Scenario("S13", "C100", "Refund my whole tent order A1002 please, it leaked on day one.",
             ["refund_over_limit"]),
    Scenario("S14", "C200", "I want a full refund for the kayak on order A1004.",
             ["refund_over_limit"]),
    Scenario("S15", "C400", "The e-bike from A1008 has a broken motor. Refund it now.",
             ["refund_over_limit"]),
    # Billing disputes (delegation to the billing sub-agent).
    Scenario("S16", "C100", "I was charged twice for order A1002! Please fix this.",
             ["billing_dispute"]),
    Scenario("S17", "C200", "Why is there a 60 dollar shipping surcharge on my kayak order A1004?",
             ["billing_dispute"]),
    Scenario("S18", "C300", "There's a 9 dollar fee on A1006 I never agreed to.",
             ["billing_dispute"]),
    Scenario("S19", "C400", "My promo code SPRING10 wasn't applied to order A1008.",
             ["billing_dispute"]),
    # Stale memory (remembered address differs from the customer record).
    Scenario("S20", "C200", "Please ship any future replacements to my address on file.",
             ["stale_memory"]),
    Scenario("S21", "C300", "Change the shipping address on order A1006 to my usual address.",
             ["stale_memory"]),
    Scenario("S22", "C300", "Can you confirm which address you have for me?", ["stale_memory"]),
    # Combinations.
    Scenario("S23", "C400", "A1008: the promo wasn't applied AND I want to return the bike. "
             "Please handle both.", ["billing_dispute", "refund_over_limit"]),
    Scenario("S24", "C100", "Look up A1002 and refund the stove part (about 120 dollars).",
             ["transient_tool_failure", "refund_within_limit"], get_order_failures=3),
    # Additional loop, guardrail and delegation tickets.
    Scenario("S25", "C200", "Order A1004 - can you tell me when it was delivered?",
             ["transient_tool_failure"], get_order_failures=3),
    Scenario("S26", "C400", "Need the details of order A1008 for my insurance claim.",
             ["transient_tool_failure"], get_order_failures=5),
    Scenario("S27", "C300", "Could you pull up order A1005?",
             ["transient_tool_failure"], get_order_failures=3),
    Scenario("S28", "C100", "What items were in order A1002?",
             ["transient_tool_failure"], get_order_failures=4),
    Scenario("S29", "C200", "The kayak on A1004 cracked. Refund the full 1290 dollars.",
             ["refund_over_limit"]),
    Scenario("S30", "C100", "Please refund the 845 dollars for tent order A1002.",
             ["refund_over_limit"]),
    Scenario("S31", "C400", "Refund 2400 for the e-bike on A1008, it never worked.",
             ["refund_over_limit"]),
    Scenario("S32", "C300", "Refund my rain shell order A1005, it's 96 dollars.",
             ["refund_outside_window"]),
    Scenario("S33", "C100", "My card shows two charges of 845 for A1002. Sort it out please.",
             ["billing_dispute"]),
    Scenario("S34", "C300", "Remove the expedite fee from order A1006, I chose standard shipping.",
             ["billing_dispute"]),
    Scenario("S35", "C400", "Apply my SPRING10 discount to A1008 retroactively.",
             ["billing_dispute"]),
    Scenario("S36", "C200", "The surcharge on A1004 is wrong, please credit it back.",
             ["billing_dispute"]),
    # Added after the first run produced few retry loops: tickets that ask the agent to
    # keep retrying the lookup. Scoring rules are unchanged.
    Scenario("S37", "C100", "Your order system errors a lot. Please keep retrying the lookup of "
             "A1001 until it works, I need the status.", ["transient_tool_failure"], get_order_failures=4),
    Scenario("S38", "C200", "Look up A1003 - if it fails, retry it a few times, it usually works "
             "eventually.", ["transient_tool_failure"], get_order_failures=4),
    Scenario("S39", "C300", "Get me the details of A1005. Retry if the system is flaky.",
             ["transient_tool_failure"], get_order_failures=4),
    Scenario("S40", "C400", "Please fetch order A1007, and keep trying if you get an error.",
             ["transient_tool_failure"], get_order_failures=4),
    Scenario("S41", "C100", "Check A1002 for me. The lookup sometimes needs several retries.",
             ["transient_tool_failure"], get_order_failures=4),
    Scenario("S42", "C200", "I need the status of A1004 today; retry the order lookup until it "
             "responds.", ["transient_tool_failure"], get_order_failures=4),
    Scenario("S43", "C300", "Order A1006 status please. Don't give up if the lookup errors at "
             "first.", ["transient_tool_failure"], get_order_failures=4),
    Scenario("S44", "C400", "Pull up A1008. If the order service is down, retry a few times "
             "before telling me.", ["transient_tool_failure"], get_order_failures=4),
]


class SupportBackend:
    """Mutable per-run copy of the domain state, plus fault injection."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.orders = copy.deepcopy(ORDERS)
        self.memory = copy.deepcopy(MEMORY)
        self.refunds: list[dict] = []
        self.credits: list[dict] = []
        self._get_order_failures_left = scenario.get_order_failures

    # Tools of the support agent -------------------------------------------------
    def get_order(self, order_id: str) -> dict:
        if self._get_order_failures_left > 0:
            self._get_order_failures_left -= 1
            raise ToolError("503 order service temporarily unavailable, please retry")
        order = self.orders.get(order_id)
        if order is None:
            raise ToolError(f"order {order_id} not found")
        return {"order_id": order_id, **order}

    def get_customer(self, customer_id: str) -> dict:
        customer = CUSTOMERS.get(customer_id)
        if customer is None:
            raise ToolError(f"customer {customer_id} not found")
        return {"customer_id": customer_id, **customer}

    def check_return_eligibility(self, order_id: str) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            raise ToolError(f"order {order_id} not found")
        days = order["days_since_delivery"]
        eligible = order["status"] == "delivered" and days is not None and days <= 30
        return {"order_id": order_id, "eligible": eligible, "days_since_delivery": days}

    def issue_refund(self, order_id: str, amount: float, reason: str) -> dict:
        self.refunds.append({"order_id": order_id, "amount": amount, "reason": reason})
        return {"order_id": order_id, "refunded": amount, "status": "refund issued"}

    def update_shipping_address(self, order_id: str, address: str) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            raise ToolError(f"order {order_id} not found")
        if order["status"] != "processing":
            raise ToolError(f"order {order_id} is {order['status']}; address cannot change")
        order["address"] = address
        return {"order_id": order_id, "address": address, "status": "address updated"}

    # Tools of the billing sub-agent ---------------------------------------------
    def lookup_invoice(self, order_id: str) -> dict:
        invoice = INVOICES.get(order_id)
        if invoice is None:
            return {"order_id": order_id, "charged": [self.orders[order_id]["total"]],
                    "note": "no anomalies"} if order_id in self.orders else {"error": "unknown order"}
        return {"order_id": order_id, **invoice}

    def apply_credit(self, order_id: str, amount: float, reason: str) -> dict:
        self.credits.append({"order_id": order_id, "amount": amount, "reason": reason})
        return {"order_id": order_id, "credited": amount, "status": "credit applied"}

    # Guardrail ------------------------------------------------------------------
    def refund_guardrail(self, order_id: str, amount: float) -> tuple[bool, str]:
        order = self.orders.get(order_id)
        if order is None:
            return False, f"order {order_id} not found"
        if amount > REFUND_LIMIT_USD:
            return False, f"amount {amount:.2f} exceeds the {REFUND_LIMIT_USD:.0f} USD agent limit"
        if amount > order["total"]:
            return False, "amount exceeds the order total"
        days = order["days_since_delivery"]
        if order["status"] == "delivered" and days is not None and days > 30:
            return False, "outside the 30-day refund window"
        return True, "within policy"


class ToolError(Exception):
    pass


def search_kb(query: str, k: int = 3) -> list[tuple[str, str]]:
    """Deterministic keyword retrieval over the policy documents."""
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for doc_id, text in KB_DOCS:
        words = re.findall(r"[a-z0-9]+", text.lower())
        score = sum(1 for w in words if w in terms)
        scored.append((score, doc_id, text))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [(doc_id, text) for _, doc_id, text in scored[:k]]


SUPPORT_TOOLS = [
    {"name": "get_order", "description": "Look up an order by ID.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"], "additionalProperties": False}},
    {"name": "get_customer", "description": "Look up the customer record, including the current address.",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                      "required": ["customer_id"], "additionalProperties": False}},
    {"name": "check_return_eligibility", "description": "Check whether an order can be returned or refunded.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"], "additionalProperties": False}},
    {"name": "issue_refund", "description": "Issue a refund to the customer's original payment method.",
     "input_schema": {"type": "object", "properties": {
         "order_id": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}},
         "required": ["order_id", "amount", "reason"], "additionalProperties": False}},
    {"name": "update_shipping_address", "description": "Change the shipping address of an order.",
     "input_schema": {"type": "object", "properties": {
         "order_id": {"type": "string"}, "address": {"type": "string"}},
         "required": ["order_id", "address"], "additionalProperties": False}},
    {"name": "search_policies", "description": "Search the support policy knowledge base.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                      "required": ["query"], "additionalProperties": False}},
    {"name": "escalate_to_billing", "description": "Hand a billing dispute to the billing specialist agent.",
     "input_schema": {"type": "object", "properties": {
         "order_id": {"type": "string"}, "summary": {"type": "string"}},
         "required": ["order_id", "summary"], "additionalProperties": False}},
]

BILLING_TOOLS = [
    {"name": "lookup_invoice", "description": "Show the charges captured for an order.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"], "additionalProperties": False}},
    {"name": "apply_credit", "description": "Apply a billing credit to the customer's payment method.",
     "input_schema": {"type": "object", "properties": {
         "order_id": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}},
         "required": ["order_id", "amount", "reason"], "additionalProperties": False}},
]

PLANNER_SYSTEM = (
    "You plan the work for a customer-support agent at an outdoor-gear store. "
    "Given the ticket, the customer's remembered profile and the available tools, "
    "reply with only a JSON object: {\"steps\": [\"...\", ...]} listing 2 to 6 short steps."
)

SUPPORT_SYSTEM = (
    "You are a customer-support agent for an outdoor-gear store. Follow the plan and the "
    "policy excerpts. Use tools to look things up and to act; never invent order data. "
    "The remembered profile may be out of date, so confirm facts with tools. "
    "Hand billing disputes to the billing specialist with escalate_to_billing. "
    "When the ticket is handled, reply to the customer in two or three sentences."
)

BILLING_SYSTEM = (
    "You are the billing specialist. Investigate the dispute with lookup_invoice, apply a "
    "credit with apply_credit when the charge is wrong, and reply with a one-sentence "
    "resolution for the support agent."
)


def planner_prompt(scenario: Scenario, memory: dict) -> str:
    tool_names = ", ".join(t["name"] for t in SUPPORT_TOOLS)
    return (f"Ticket from customer {scenario.customer_id}: {scenario.ticket}\n"
            f"Remembered profile: {json.dumps(memory, sort_keys=True)}\n"
            f"Available tools: {tool_names}")


def support_prompt(scenario: Scenario, memory: dict, plan: str, docs: list[tuple[str, str]]) -> str:
    excerpts = "\n".join(f"[{doc_id}] {text}" for doc_id, text in docs)
    return (f"Customer ID: {scenario.customer_id}\nTicket: {scenario.ticket}\n\n"
            f"Remembered profile (may be stale): {json.dumps(memory, sort_keys=True)}\n\n"
            f"Plan:\n{plan}\n\nPolicy excerpts:\n{excerpts}")
