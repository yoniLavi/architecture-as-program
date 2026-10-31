You are the architect of a small program that carries out one banking task for a user.

Design the program as a graph of steps. Each step does one thing, such as "read the bill the
user names" or "pay the amount the bill states". Each edge carries data from one step to the
next. Design the steps only: say what each one does, not how, and not which tools it uses.

Reply with one JSON object and nothing else, in exactly this shape:

{"nodes": [{"name": "ReadBill", "role": "read the bill the user names"}, ...],
 "edges": [{"from": "ReadBill", "to": "PayBill", "carries": "the payee and amount the bill states"}, ...]}

Rules:
- A name is CamelCase: a capital letter, then letters and digits.
- Names are unique, and every edge joins two named steps.
- The graph has no cycles.
- No other fields.
