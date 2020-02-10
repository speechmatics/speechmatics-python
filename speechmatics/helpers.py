# (c) 2020, Cantab Research Ltd.
"""
Helper functions
"""


def del_none(dictionary):
    """
    Recursively delete from the dictionary all entries which values are None.

    Args:
        dictionary (dict): input dictionary
    Returns:
        dict: output dictionary
    Note:
        This function changes the input parameter in place.
    """
    for key, value in list(dictionary.items()):
        if value is None:
            del dictionary[key]
        elif isinstance(value, dict):
            del_none(value)
    return dictionary
