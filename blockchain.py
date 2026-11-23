from datetime import datetime, timezone
from security import sha256_text

def make_block(identity_id, data_hash, previous_hash, idx):
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = f"{idx}|{timestamp}|{identity_id}|{data_hash}|{previous_hash}"
    return {"idx": idx, "timestamp": timestamp, "identity_id": identity_id,
            "data_hash": data_hash, "previous_hash": previous_hash,
            "block_hash": sha256_text(payload)}

def verify_chain(blocks):
    previous = "0" * 64
    for expected_idx, block in enumerate(blocks, start=1):
        if block["idx"] != expected_idx or block["previous_hash"] != previous:
            return False
        payload = f'{block["idx"]}|{block["timestamp"]}|{block["identity_id"]}|{block["data_hash"]}|{block["previous_hash"]}'
        if sha256_text(payload) != block["block_hash"]:
            return False
        previous = block["block_hash"]
    return True
