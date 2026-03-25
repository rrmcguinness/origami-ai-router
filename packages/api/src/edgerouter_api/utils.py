def deep_merge(dict1, dict2):
    """
    Recursively merges dict2 into dict1.
    Values in dict2 will override values in dict1.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            if isinstance(dict1[key], dict):
                deep_merge(dict1[key], value)
            elif hasattr(dict1[key], "__dict__"):
                # If dict1[key] is an object (like BaseConfig), convert it to dict, merge, and re-assign
                merged = deep_merge(dict1[key].__dict__, value)
                dict1[key] = type(dict1[key])(merged)
            else:
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1