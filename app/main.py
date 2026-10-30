"""Checkout API: the "patient" the SRE agent will heal.

FAILURE_RATE (0.0-1.0) makes a revision fail that share of /checkout requests.
Deploy a good revision with FAILURE_RATE=0, then a bad one with FAILURE_RATE=0.5.
"""
import logging
import os
import random
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("checkout")

FAILURE_RATE = float(os.environ.get("FAILURE_RATE", "0"))
VERSION = os.environ.get("APP_VERSION", "v1")
REVISION = os.environ.get("K_REVISION", "local")


@app.get("/")
def health():
    return jsonify(status="ok", version=VERSION, revision=REVISION)


@app.post("/checkout")
@app.get("/checkout")
def checkout():
    order_id = str(uuid.uuid4())[:8]
    if random.random() < FAILURE_RATE:
        # Same message every time so the agent has clear evidence to cite.
        log.error("checkout failed order=%s version=%s: PaymentGatewayTimeout "
                  "connecting to payments.internal:443", order_id, VERSION)
        return jsonify(error="payment gateway timeout", order_id=order_id), 503
    amount = (request.get_json(silent=True) or {}).get("amount", 100000)
    log.info("checkout ok order=%s amount=%s version=%s", order_id, amount, VERSION)
    return jsonify(order_id=order_id, status="paid", version=VERSION)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
