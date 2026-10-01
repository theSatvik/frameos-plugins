---
type: regex
target: last_message
# returned times are seconds; the user should see mm:ss
match: not_contains
weight: 0.5
---
\b(?:721\.8|731\.4|744\.2|757\.3|772\.0|786\.0|812\.4|845\.0|871\.2)\b
