from app.adapters.payment import verify_duplicate

def test_no_provider_duplicate_reference_means_no_refund():
    p = {"provider_duplicate_reference": False, "transactions": [
        {"transaction_id":"a","amount":49,"status":"succeeded","duplicate_group":"g"},
        {"transaction_id":"b","amount":49,"status":"succeeded","duplicate_group":"g"}]}
    assert verify_duplicate(p) == (False, 0.0, None)

def test_provider_confirmed_duplicate_returns_second_transaction():
    p = {"provider_duplicate_reference": True, "transactions": [
        {"transaction_id":"a","amount":49,"status":"succeeded","duplicate_group":"g"},
        {"transaction_id":"b","amount":49,"status":"succeeded","duplicate_group":"g"}]}
    assert verify_duplicate(p) == (True, 49.0, "b")
