import re
import unicodedata
import regex


def remove_symbols(s: str):
    """
    Replace any other markers, symbols, punctuations with a space, keeping diacritics

    Args:
        s (str): raw input transcript

    Returns:
        s (str): same string which has been modified inplace
    """
    return "".join(
        " " if unicodedata.category(c)[0] in "MSP" else c
        for c in unicodedata.normalize("NFKC", s)
    )


class BasicTextNormalizer:
    def __init__(self, remove_diacritics: bool = False, split_letters: bool = False):
        self.remove_diacritics = remove_diacritics
        self.split_letters = split_letters

        # non-ASCII letters that are not separated by "NFKD" normalization
        self.additional_diacritics = {
            "œ": "oe",
            "Œ": "OE",
            "ø": "o",
            "Ø": "O",
            "æ": "ae",
            "Æ": "AE",
            "ß": "ss",
            "ẞ": "SS",
            "đ": "d",
            "Đ": "D",
            "ð": "d",
            "Ð": "D",
            "þ": "th",
            "Þ": "th",
            "ł": "l",
            "Ł": "L",
        }

    def remove_symbols_and_diacritics(self, s: str, keep=""):
        """
        Replace any other markers, symbols, and punctuations with a space,
        and drop any diacritics (category 'Mn' and some manual mappings)
        """
        return "".join(
            c
            if c in keep
            else self.additional_diacritics[c]
            if c in self.additional_diacritics
            else ""
            if unicodedata.category(c) == "Mn"
            else " "
            if unicodedata.category(c)[0] in "MSP"
            else c
            for c in unicodedata.normalize("NFKD", s)
        )

    def clean(self, s: str):
        "Return a string without symbols and optionally without diacritics, given input string"
        if self.remove_diacritics is True:
            return self.remove_symbols_and_diacritics(s)
        return remove_symbols(s)

    def __call__(self, s: str) -> str:
        """
        Return a normalised string, given an input string, using the following modifications:

            Makes everything lowercase.
            Remove tokens between brackets.
            Replace diacritics with the ASCII eqivalent.
            Replace whitespace and any remaining punctuation with single space.
        """

        s = s.lower()

        s = re.sub(r"[<\[][^>\]]*[>\]]", "", s)
        s = re.sub(r"\(([^)]+?)\)", "", s)

        s = self.clean(s).lower()

        # insert a single space between characters in a string
        if self.split_letters:
            s = " ".join(regex.findall(r"\X", s, re.UNICODE))

        s = re.sub(r"\s+", " ", s)

        return s
