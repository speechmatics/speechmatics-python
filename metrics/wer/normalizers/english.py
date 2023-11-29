import yaml
import os
import re
from fractions import Fraction
from typing import Iterator, List, Match, Optional, Union, Tuple, Dict

from more_itertools import windowed

from .basic import BasicTextNormalizer


def postprocess(s: str):
    def combine_cents(match: Match):
        try:
            currency = match.group(1)
            integer = match.group(2)
            cents = int(match.group(3))
            return f"{currency}{integer}.{cents:02d}"
        except ValueError:
            return match.string

    def extract_cents(match: Match):
        try:
            return f"¢{int(match.group(1))}"
        except ValueError:
            return match.string

    # apply currency postprocessing; "$2 and ¢7" -> "$2.07"
    s = re.sub(r"([€£$])([0-9]+) (?:and )?¢([0-9]{1,2})\b", combine_cents, s)
    s = re.sub(r"[€£$]0.([0-9]{1,2})\b", extract_cents, s)

    # write "one(s)" instead of "1(s)", just for the readability
    s = re.sub(r"\b1(s?)\b", r"one\1", s)

    return s


class EnglishNumberNormalizer:
    """
    Convert any spelled-out numbers into arabic numbers, while handling:

    - remove any commas
    - keep the suffixes such as: `1960s`, `274th`, `32nd`, etc.
    - spell out currency symbols after the number. e.g. `$20 million` -> `20000000 dollars`
    - spell out `one` and `ones`
    - interpret successive single-digit numbers as nominal: `one oh one` -> `101`
    """

    def __init__(self):
        super().__init__()

        self.zeros = {"o", "oh", "zero"}
        self.ones = {
            name: i
            for i, name in enumerate(
                [
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "six",
                    "seven",
                    "eight",
                    "nine",
                    "ten",
                    "eleven",
                    "twelve",
                    "thirteen",
                    "fourteen",
                    "fifteen",
                    "sixteen",
                    "seventeen",
                    "eighteen",
                    "nineteen",
                ],
                start=1,
            )
        }
        self.ones_plural = {
            "sixes" if name == "six" else name + "s": (value, "s")
            for name, value in self.ones.items()
        }
        self.ones_ordinal = {
            "zeroth": (0, "th"),
            "first": (1, "st"),
            "second": (2, "nd"),
            "third": (3, "rd"),
            "fifth": (5, "th"),
            "twelfth": (12, "th"),
            **{
                name + ("h" if name.endswith("t") else "th"): (value, "th")
                for name, value in self.ones.items()
                if value > 3 and value != 5 and value != 12
            },
        }
        self.ones_suffixed = {**self.ones_plural, **self.ones_ordinal}

        self.tens = {
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
        }
        self.tens_plural = {
            name.replace("y", "ies"): (value, "s") for name, value in self.tens.items()
        }
        self.tens_ordinal = {
            name.replace("y", "ieth"): (value, "th")
            for name, value in self.tens.items()
        }
        self.tens_suffixed = {**self.tens_plural, **self.tens_ordinal}

        self.multipliers = {
            "hundred": 100,
            "thousand": 1_000,
            "million": 1_000_000,
            "billion": 1_000_000_000,
            "trillion": 1_000_000_000_000,
            "quadrillion": 1_000_000_000_000_000,
            "quintillion": 1_000_000_000_000_000_000,
            "sextillion": 1_000_000_000_000_000_000_000,
            "septillion": 1_000_000_000_000_000_000_000_000,
            "octillion": 1_000_000_000_000_000_000_000_000_000,
            "nonillion": 1_000_000_000_000_000_000_000_000_000_000,
            "decillion": 1_000_000_000_000_000_000_000_000_000_000_000,
        }
        self.multipliers_plural = {
            name + "s": (value, "s") for name, value in self.multipliers.items()
        }
        self.multipliers_ordinal = {
            name + "th": (value, "th") for name, value in self.multipliers.items()
        }
        self.multipliers_suffixed = {
            **self.multipliers_plural,
            **self.multipliers_ordinal,
        }
        self.decimals = {*self.ones, *self.tens, *self.zeros}

        self.preceding_prefixers = {
            "minus": "-",
            "negative": "-",
            "plus": "+",
            "positive": "+",
        }
        self.following_prefixers = {
            "pound": "£",
            "pounds": "£",
            "euro": "€",
            "euros": "€",
            "dollar": "$",
            "dollars": "$",
            "cent": "¢",
            "cents": "¢",
        }
        self.prefixes = set(
            list(self.preceding_prefixers.values())
            + list(self.following_prefixers.values())
        )
        self.suffixers = {
            "per": {"cent": "%"},
            "percent": "%",
        }
        self.specials = {"and", "double", "triple", "point"}

        self.words = {
            key
            for mapping in [
                self.zeros,
                self.ones,
                self.ones_suffixed,
                self.tens,
                self.tens_suffixed,
                self.multipliers,
                self.multipliers_suffixed,
                self.preceding_prefixers,
                self.following_prefixers,
                self.suffixers,
                self.specials,
            ]
            for key in mapping
        }
        self.literal_words = {"one", "ones"}

    def process_words(self, words: List[str]) -> Iterator[str]:
        prefix: Optional[str] = None
        value: Optional[Union[str, int]] = None
        skip: bool = False

        def to_fraction(s: str) -> Union[Fraction, None]:
            "Convert input string into a Fraction object or return None"
            try:
                return Fraction(s)
            except ValueError:
                return None

        def output(result: Union[str, int]):
            """
            Prepend any prefix to result and return as a string.

            Reset the prefix and value to None.
            """
            nonlocal prefix, value
            result = str(result)

            if prefix is not None:
                result = prefix + result

            value, prefix = None, None
            return result

        if len(words) == 0:
            return

        for prev_word, current_word, next_word in windowed([None] + words + [None], 3):
            if skip is True:
                skip = False
                continue

            assert isinstance(current_word, str)
            # find if next word is an integer or float string
            next_is_numeric: bool = next_word is not None and bool(
                re.match(r"^\d+(\.\d+)?$", next_word)
            )
            has_prefix: bool = current_word[0] in self.prefixes
            current_without_prefix: str = (
                current_word[1:] if has_prefix else current_word
            )
            if re.match(r"^\d+(\.\d+)?$", current_without_prefix):
                # arabic numbers (potentially with signs and fractions)
                frac = to_fraction(current_without_prefix)
                assert frac is not None
                if value is not None:
                    if isinstance(value, str) and value.endswith("."):
                        # concatenate decimals / ip address components
                        value = str(value) + str(current_word)
                        continue
                    yield output(value)

                prefix = current_word[0] if has_prefix else prefix
                if frac.denominator == 1:
                    value = frac.numerator  # int
                else:
                    value = current_without_prefix  # str
            elif current_word not in self.words:
                # non-numeric words
                if value is not None:
                    yield output(value)
                yield output(current_word)
            elif current_word in self.zeros:
                value = str(value or "") + "0"
            elif current_word in self.ones:
                ones = self.ones[current_word]

                if value is None:
                    value = ones
                elif isinstance(value, str) or prev_word in self.ones:
                    # replace the last zero with the digit
                    if prev_word in self.tens and ones < 10:
                        value = str(value)
                        if value and value[-1] == "0":
                            value = value[:-1] + str(ones)
                    else:
                        value = str(value) + str(ones)
                elif ones < 10:
                    if value % 10 == 0:
                        value += ones
                    else:
                        value = str(value) + str(ones)
                else:  # eleven to nineteen
                    if value % 100 == 0:
                        value += ones
                    else:
                        value = str(value) + str(ones)
            elif current_word in self.ones_suffixed:
                # ordinal or cardinal; yield the number right away
                ones, suffix = self.ones_suffixed[current_word]
                if value is None:
                    yield output(str(ones) + suffix)
                elif isinstance(value, str) or prev_word in self.ones:
                    if prev_word in self.tens and ones < 10:
                        value = str(value)
                        yield output(value[:-1] + str(ones) + suffix)
                    else:
                        yield output(str(value) + str(ones) + suffix)
                elif ones < 10:
                    if value % 10 == 0:
                        yield output(str(value + ones) + suffix)
                    else:
                        yield output(str(value) + str(ones) + suffix)
                else:  # eleven to nineteen
                    if value % 100 == 0:
                        yield output(str(value + ones) + suffix)
                    else:
                        yield output(str(value) + str(ones) + suffix)
                value = None
            elif current_word in self.tens:
                tens = self.tens[current_word]
                if value is None:
                    value = tens
                elif isinstance(value, str):
                    value = str(value) + str(tens)
                else:
                    if value % 100 == 0:
                        value += tens
                    else:
                        value = str(value) + str(tens)
            elif current_word in self.tens_suffixed:
                # ordinal or cardinal; yield the number right away
                tens, suffix = self.tens_suffixed[current_word]
                if value is None:
                    yield output(str(tens) + suffix)
                elif isinstance(value, str):
                    yield output(str(value) + str(tens) + suffix)
                else:
                    if value % 100 == 0:
                        yield output(str(value + tens) + suffix)
                    else:
                        yield output(str(value) + str(tens) + suffix)
            elif current_word in self.multipliers:
                multiplier = self.multipliers[current_word]
                if value is None:
                    value = multiplier
                elif isinstance(value, str) or value == 0:
                    frac = to_fraction(str(value))
                    multiplied_frac = frac * multiplier if frac is not None else None
                    if frac is not None and multiplied_frac.denominator == 1:
                        value = multiplied_frac.numerator
                    else:
                        yield output(value)
                        value = multiplier
                else:
                    before = value // 1000 * 1000
                    residual = value % 1000
                    value = before + residual * multiplier
            elif current_word in self.multipliers_suffixed:
                multiplier, suffix = self.multipliers_suffixed[current_word]
                if value is None:
                    yield output(str(multiplier) + suffix)
                elif isinstance(value, str):
                    frac = to_fraction(value)
                    multiplied_frac = frac * multiplier if frac is not None else None
                    if frac is not None and multiplied_frac.denominator == 1:
                        yield output(str(multiplied_frac.numerator) + suffix)
                    else:
                        yield output(value)
                        yield output(str(multiplier) + suffix)
                else:  # int
                    before = value // 1000 * 1000
                    residual = value % 1000
                    value = before + residual * multiplier
                    yield output(str(value) + suffix)
                value = None
            elif current_word in self.preceding_prefixers:
                # apply prefix (positive, minus, etc.) if it precedes a number
                if value is not None:
                    yield output(value)

                if next_word in self.words or next_is_numeric:
                    prefix = self.preceding_prefixers[current_word]
                else:
                    yield output(current_word)
            elif current_word in self.following_prefixers:
                # apply prefix (dollars, cents, etc.) only after a number
                if value is not None:
                    prefix = self.following_prefixers[current_word]
                    yield output(value)
                else:
                    yield output(current_word)
            elif current_word in self.suffixers:
                # apply suffix symbols (percent -> '%')
                if value is not None:
                    suffix = self.suffixers[current_word]
                    if isinstance(suffix, dict):
                        if next_word in suffix:
                            yield output(str(value) + suffix[next_word])
                            skip = True
                        else:
                            yield output(value)
                            yield output(current_word)
                    else:
                        yield output(str(value) + suffix)
                else:
                    yield output(current_word)
            elif current_word in self.specials:
                if next_word not in self.words and not next_is_numeric:
                    # apply special handling only if the next word can be numeric
                    if value is not None:
                        yield output(value)
                    yield output(current_word)
                elif current_word == "and":
                    # ignore "and" after hundreds, thousands, etc.
                    if prev_word not in self.multipliers:
                        if value is not None:
                            yield output(value)
                        yield output(current_word)
                elif current_word in ("double", "triple"):
                    if next_word in self.ones or next_word in self.zeros:
                        repeats = 2 if current_word == "double" else 3
                        ones = self.ones.get(next_word, 0)
                        value = str(value or "") + str(ones) * repeats
                        skip = True
                    else:
                        if value is not None:
                            yield output(value)
                        yield output(current_word)
                elif current_word == "point":
                    if next_word in self.decimals or next_is_numeric:
                        value = str(value or "") + "."
                else:
                    raise ValueError(f"Unexpected token: {current_word}")
            else:
                raise ValueError(f"Unexpected token: {current_word}")

        if value is not None:
            yield output(value)

    def preprocess(self, s: str):
        """
        Function standardises spacing between entities before processing

        Args:
            s (str): The string to be preprocessed

        Returns:
            s (str): the preprocessed string, with entities standardised
        """
        # replace "<number> and a half" with "<number> point five"
        results = []

        segments = re.split(r"\band\s+a\s+half\b", s)
        for i, segment in enumerate(segments):
            if len(segment.strip()) == 0:
                continue
            if i == len(segments) - 1:
                results.append(segment)
            else:
                results.append(segment)
                last_word = segment.rsplit(maxsplit=2)[-1]
                if last_word in self.decimals or last_word in self.multipliers:
                    results.append("point five")
                else:
                    results.append("and a half")

        s = " ".join(results)

        # put a space at number/letter boundary. e.g., AA00 AAA -> AA 00 AA
        s = re.sub(r"([a-z])([0-9])", r"\1 \2", s)
        s = re.sub(r"([0-9])([a-z])", r"\1 \2", s)

        # but remove spaces which could be a suffix. e.g., 21 st -> 21st
        s = re.sub(r"([0-9])\s+(st|nd|rd|th|s)\b", r"\1\2", s)

        return s

    def __call__(self, s: str):
        s = self.preprocess(s)
        s = " ".join(word for word in self.process_words(s.split()) if word is not None)
        s = postprocess(s)

        return s


class EnglishTextNormalizer(BasicTextNormalizer):
    def __init__(self, remove_disfluencies=True):
        super().__init__()

        config_path = os.path.join(os.path.dirname(__file__), "english.yaml")
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        self.remove_disfluencies = remove_disfluencies
        self.replacers, self.disfluencies, self.spellings = self.parse_config(config)
        self.standardize_numbers = EnglishNumberNormalizer()

    def parse_config(
        self, config: dict
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
        contractions_and_abbreviations: dict = config["standalone contractions"]

        # add appropriate spaces
        for replacement_type in ["perfect", "general contractions"]:
            contractions_and_abbreviations.update(
                {f" {key}": value for key, value in config[replacement_type].items()}
            )
        contractions_and_abbreviations.update(
            {f"{key} ": value for key, value in config["titles"].items()}
        )

        return (
            contractions_and_abbreviations,
            config["disfluencies"],
            config["spellings"],
        )

    def __call__(self, s: str):
        s = s.lower()

        # remove words between square / rounded brackets
        s = re.sub(r"[<\[][^>\]]*[>\]]", "", s)
        s = re.sub(r"\(([^)]+?)\)", "", s)

        # remove disfluencies or map to standards
        if self.remove_disfluencies:
            s = re.sub("|".join(self.disfluencies.values()), "", s)
        else:
            for replacement, pattern in self.disfluencies.items():
                s = re.sub(pattern, replacement, s)

        # standardize when there's a space before an apostrophe
        s = re.sub(r"\s+'", "'", s)

        # expand contractions using mapping
        for replacement, pattern in self.replacers.items():
            s = re.sub(pattern, replacement, s)

        # remove commas between digits and remove full stops not followed by digits
        s = re.sub(r"(\d),(\d)", r"\1\2", s)
        s = re.sub(r"\.([^0-9]|$)", r" \1", s)

        # keep some symbols for numerics
        s = self.remove_symbols_and_diacritics(s, keep=".%$¢€£")

        # standardise numbers and spellings
        s = self.standardize_numbers(s)
        s = " ".join(self.spellings.get(word, word) for word in s.split())

        # now remove prefix/suffix symbols that are not preceded/followed by numbers
        s = re.sub(r"[.$¢€£]([^0-9])", r" \1", s)
        s = re.sub(r"([^0-9])%", r"\1 ", s)

        # replace any successive whitespace characters with a space
        s = re.sub(r"\s+", " ", s)

        return s
