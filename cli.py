"""Requirements Accelerator, v1 script. No UI: run this from a terminal.

python cli.py

Covers layer 00 only (the problem). Layers 01-09 are follow-up slices of e5; this proves
the ledger, the gate and redirect, the reflection checkpoint, and the output renderer work
end to end before the rest of the layers repeat the same pattern.
"""

from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00
from engine.render import render_business_ask, render_readiness_block


def main():
    print("Requirements Accelerator (v1, layer 00 only)")
    print("=" * 60)
    print()

    ledger = Ledger()
    reasoner = StubReasoner()
    run_layer_00(ledger, reasoner)

    print()
    print("=" * 60)
    print()
    print(render_business_ask(ledger))
    print()
    print(render_readiness_block(ledger))


if __name__ == "__main__":
    main()
