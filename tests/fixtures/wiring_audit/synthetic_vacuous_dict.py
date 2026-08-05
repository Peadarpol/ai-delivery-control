def dummy_session_consumer():
    sdata = {"token_usage": {}}
    
    # Read token_usage
    usage = sdata.get("token_usage", {})
    
    # Reassign token_usage to a vacuous literal
    sdata["token_usage"] = {}
