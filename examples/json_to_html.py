from dataclasses import dataclass
from datetime import timedelta
import json
from typing import Dict, Iterator, List, Optional
from jinja2 import BaseLoader, Environment
from pathlib import Path
from argparse import ArgumentParser
from itertools import groupby
from speechmatics.adapters import join_tokens

COLORS = ["#800000", "#9A6324", "#808000", "#469990", "#000075"]

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>{{ title or 'Podcast Transcript' }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style type="text/css">
        /* General Typography */
        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 300;
            src: url("https://speechmatics.com/static/fonts/Inter-Light.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 400;
            src: url("https://speechmatics.com/static/fonts/Inter-Regular.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 500;
            src: url("https://speechmatics.com/static/fonts/Inter-Medium.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 600;
            src: url("https://speechmatics.com/static/fonts/Inter-SemiBold.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 700;
            src: url("https://speechmatics.com/static/fonts/Inter-Bold.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 800;
            src: url("https://speechmatics.com/static/fonts/Inter-ExtraBold.woff2") format("woff2");
        }

        @font-face {
            font-display: swap;
            font-family: 'Inter';
            font-weight: 900;
            src: url("https://speechmatics.com/static/fonts/Inter-Black.woff2") format("woff2");
        }


        body {
            font-family: 'Inter';
            line-height: 1.6;
            font-size: 1.1rem;
            color: #333;
            margin: 0;
            padding: 0;
        }

        /* Article Structure */
        article {
            max-width: 800px;
            /* Example value, adjust as needed */
            margin: 0 auto;
            /* Center the article */
            padding: 2rem;
            /* Space around the article content */
            background-color: #fff;
            /* Background color for the article */
            border-radius: 5px;
            /* Rounded corners */
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            /* Subtle shadow for depth */
        }

        details {
            margin-bottom: 0.5em;
        }

        /* Headings */
        h1,
        h2 {
            margin-top: 0;
            /* No margin at the top of the first heading */
            margin-bottom: 1rem;
            /* Space below headings */
        }

        /* Speaker Citation */
        cite {
            font-weight: bold;
            /* Bold speaker names */
            color: #555;
            /* Lighter color for speaker names */
        }

        /* Timestamp */
        time {
            font-size: 0.8em;
            /* Smaller font size for timestamps */
            color: #777;
            /* Light gray color for timestamps */
        }

        /* Transcript Entries */
        div {
            margin-bottom: 1rem;
            /* Space between entries */
        }

        /* Responsive Adjustments */
        @media (max-width: 600px) {
            article {
                padding: 1rem;
                /* Reduced padding on smaller screens */
            }

            h1,
            h2 {
                font-size: 1.5em;
                /* Larger font size for headings on small screens */
            }
        }

        footer {
            display: grid;
            justify-items: center;
            /* Centers items horizontally */
        }

        footer p {
            font-style: italic;
            font-size: 0.75em;
            margin-bottom: 5px;
        }

        footer {
            margin-bottom: 20px;
        }
    </style>
    <link rel="preload" href="https://speechmatics.com/static/fonts/Inter-Regular.woff2" as="font" type="font/woff"
        crossorigin="" />
    <link rel="preload" href="https://speechmatics.com/static/fonts/Inter-Medium.woff2" as="font" type="font/woff"
        crossorigin="" />
    <link rel="preload" href="https://speechmatics.com/static/fonts/Inter-SemiBold.woff2" as="font" type="font/woff"
        crossorigin="" />
    <link rel="preload" href="https://speechmatics.com/static/fonts/Inter-Bold.woff2" as="font" type="font/woff"
        crossorigin="" />
</head>

<body>
    <article>
        {% if title %}
        <h1>{{ title }}</h1>
        {% endif %}
        {% if summary %}
        <details open>
            <summary>Podcast summary</summary>
            <p>{{ summary }}</p>
        </details>
        {% endif %}
        <section>
            {% for entry in transcript_entries %}
            <div>
                <cite style="color: {{ entry.speaker_color or '#000' }}">{{ entry.speaker }}</cite>
                <time style="color: {{ entry.speaker_color or '#000' }}">{{ entry.timestamp.__str__().split(".", 2)[0]
                    }}</time>
                <p>{{ entry.sentence }}</p>
            </div>
            {% endfor %}
        </section>
    </article>

    <footer>
        <p>transcribed by</p>
        <svg version="1.1" xmlns="https://www.w3.org/2000/svg" viewBox="0 0 154.2 47" xml:space="preserve"
            width="137px">
            <g>
                <g>
                    <g>
                        <path
                            d="M0.9,37.1l2.6-0.8c0.3,2.2,2,3.7,4.1,3.7c2,0,3.4-1,3.4-2.4c0-4.1-9.4-1.8-9.4-8c0-2.7,2.5-4.6,5.9-4.6 c3.2,0,5.8,1.7,6.2,4.3l-2.6,1.1c-0.3-1.7-1.7-2.9-3.7-2.9c-1.9,0-3,0.8-3,2.1c0,3.5,9.4,1.1,9.4,8c0,3-2.5,5-6.4,5 C4.2,42.4,1.4,40.2,0.9,37.1z">
                        </path>
                        <path
                            d="M15.7,29.8h2.7v1.6c0.7-1,2.1-1.8,3.9-1.8c3.7,0,5.8,2.7,5.8,6.4c0,3.7-2.3,6.4-6,6.4c-1.5,0-3-0.6-3.7-1.6v5.9h-2.7 V29.8z M21.8,40.1c2.2,0,3.6-1.6,3.6-4.1c0-2.5-1.4-4.1-3.6-4.1c-2.2,0-3.6,1.6-3.6,4.1C18.2,38.5,19.7,40.1,21.8,40.1z">
                        </path>
                        <path
                            d="M35.4,29.6c4,0,6.1,2.9,6.1,5.9c0,0.4,0,0.9,0,1.1h-9.5c0.2,2.1,1.6,3.5,3.6,3.5c1.6,0,2.8-0.8,3.1-2.1l2.5,0.6 c-0.7,2.4-2.8,3.8-5.7,3.8c-3.9,0-6.2-3.1-6.2-6.4C29.3,32.7,31.4,29.6,35.4,29.6z M38.6,34.6c-0.2-1.7-1.3-2.9-3.2-2.9 c-1.7,0-2.9,1-3.3,2.9H38.6z">
                        </path>
                        <path
                            d="M48.7,29.6c4,0,6.1,2.9,6.1,5.9c0,0.4,0,0.9,0,1.1h-9.5c0.2,2.1,1.6,3.5,3.6,3.5c1.6,0,2.8-0.8,3.1-2.1l2.5,0.6 c-0.7,2.4-2.8,3.8-5.7,3.8c-3.9,0-6.2-3.1-6.2-6.4C42.7,32.7,44.8,29.6,48.7,29.6z M52,34.6c-0.2-1.7-1.3-2.9-3.2-2.9 c-1.7,0-2.9,1-3.3,2.9H52z">
                        </path>
                        <path
                            d="M56,36c0-3.8,2.5-6.4,6.2-6.4c3.1,0,5.2,1.6,5.7,4.2l-2.6,0.5c-0.2-1.4-1.4-2.4-3-2.4c-2.1,0-3.5,1.6-3.5,4.1 c0,2.5,1.4,4.1,3.5,4.1c1.6,0,2.7-0.9,3-2.3l2.6,0.5c-0.5,2.6-2.7,4.1-5.7,4.1C58.5,42.4,56,39.8,56,36z">
                        </path>
                        <path
                            d="M69.8,24.8h2.7V32c0.9-1.6,2.3-2.3,4.1-2.3c2.8,0,4.7,1.7,4.7,4.5v8.1h-2.7v-7.5c0-1.6-1-2.7-2.7-2.7 c-2.1,0-3.3,1.8-3.3,4.8v5.4h-2.7V24.8z">
                        </path>
                        <path
                            d="M83.7,29.8h2.7v2.1c0.7-1.4,1.8-2.3,3.6-2.3c2,0,3.4,0.9,3.9,2.5c0.7-1.4,2.1-2.5,4.1-2.5c2.7,0,4.4,1.7,4.4,4.2v8.4 h-2.7v-7.7c0-1.6-0.9-2.6-2.5-2.6c-1.8,0-2.9,1.6-2.9,4v6.3h-2.7v-7.7c0-1.6-0.9-2.6-2.4-2.6c-1.8,0-2.9,1.6-2.9,4v6.3h-2.7V29.8 z">
                        </path>
                        <path
                            d="M109.7,31.8c-1.5,0-2.6,0.9-2.7,2.4l-2.4-0.4c0.4-2.4,2.5-4,5.1-4c3.1,0,5.3,1.8,5.3,4.9v7.7h-2.6v-1.9 c-0.7,1.3-2.2,2.1-3.9,2.1c-2.5,0-4.2-1.6-4.2-3.7c0-2.4,1.9-3.7,5.7-4.1l2.3-0.2v-0.2C112.4,32.7,111.3,31.8,109.7,31.8z M109,40.4c2.1,0,3.3-1.5,3.3-3.5v-0.5l-2.4,0.3c-2,0.2-3.1,1-3.1,2C106.9,39.7,107.8,40.4,109,40.4z">
                        </path>
                        <path
                            d="M122.6,42.4c-2.3,0-4.1-1.3-4.1-4.1v-6.2h-2.2v-2.3h2.2v-3.7h2.7v3.7h3.2v2.3h-3.2v6.1c0,1.2,0.7,1.9,1.7,1.9 c0.5,0,1-0.1,1.5-0.3l0.2,2.4C124,42.3,123.3,42.4,122.6,42.4z">
                        </path>
                        <path
                            d="M127.5,24.3c1,0,1.8,0.8,1.8,1.7c0,1-0.8,1.7-1.8,1.7c-1,0-1.7-0.8-1.7-1.7C125.8,25.1,126.6,24.3,127.5,24.3z M126.2,29.8h2.7v12.4h-2.7V29.8z">
                        </path>
                        <path
                            d="M130.8,36c0-3.8,2.5-6.4,6.2-6.4c3.1,0,5.2,1.6,5.7,4.2l-2.6,0.5c-0.2-1.4-1.4-2.4-3-2.4c-2.1,0-3.5,1.6-3.5,4.1 c0,2.5,1.4,4.1,3.5,4.1c1.6,0,2.7-0.9,3-2.3l2.6,0.5c-0.5,2.6-2.7,4.1-5.7,4.1C133.3,42.4,130.8,39.8,130.8,36z">
                        </path>
                    </g>
                    <g>
                        <path
                            d="M143.3,38.8l2.2-0.9c0.4,1.3,1.4,2.4,3.1,2.4c1.3,0,2.1-0.7,2.1-1.6c0-2.7-6.9-0.9-6.9-5.6c0-1.9,1.7-3.4,4.4-3.4 c2.3,0,4.3,1.2,4.8,3.1l-2.2,0.9c-0.3-1.2-1.5-1.9-2.6-1.9c-1.2,0-1.9,0.5-1.9,1.3c0,2.4,7,0.6,7,5.7c0,2.1-1.9,3.8-4.7,3.8 C145.6,42.4,143.8,40.6,143.3,38.8z">
                        </path>
                    </g>
                </g>
                <g>
                    <g>
                        <path fill="#CACACA"
                            d="M68.3,9.1c0-2.3,0.9-4.3,2.3-5.9c-0.2,0.2-0.3,0.3-0.5,0.5c-3.8,4.3-9,3.4-9,3.4c7.2,7.4,10.3,9.2,12.5,10 C70.5,15.8,68.3,12.7,68.3,9.1z">
                        </path>
                    </g>
                    <g>
                        <path fill="#92C3BB" d="M80.7,1.1L80.6,1l0,0C80.6,1,80.7,1.1,80.7,1.1z"></path>
                        <polygon fill="#92C3BB" points="81,1.2 81,1.2 81,1.2 "></polygon>
                        <path fill="#CACACA"
                            d="M80.6,1c0.1,0,0.9,0.5,1,0.5c0,0,0,0,0,0c2.6,1.5,4.3,4.3,4.3,7.5c0,2.2-0.8,4.3-2.2,5.9 c0.2-0.2,0.3-0.3,0.5-0.5c3.8-4.3,9-3.4,9-3.4C85.8,3.6,82.8,1.9,80.6,1z">
                        </path>
                    </g>
                    <path
                        d="M89.1,7.1c9.6,10.1,13.9,10.6,16,10.6c4.8,0,8.7-3.9,8.7-8.7c0-4.8-3.9-8.7-8.7-8.7c-0.5,0-3.6-0.3-6.8,3.3 C94.7,7.9,89.1,7.1,89.1,7.1z M105.4,4.5c2.5,0,4.5,2.1,4.5,4.6c0,2.5-2,4.6-4.5,4.6s-4.5-2.1-4.5-4.6 C100.8,6.5,102.8,4.5,105.4,4.5z">
                    </path>
                    <path
                        d="M77.1,0.3c-4.8,0-8.8,3.9-8.8,8.8c0,4.8,3.9,8.8,8.8,8.8c4.8,0,8.8-3.9,8.8-8.8C85.9,4.2,81.9,0.3,77.1,0.3z M77.1,13.6 c-2.5,0-4.5-2.1-4.5-4.6c0-2.5,2-4.6,4.5-4.6c2.5,0,4.5,2.1,4.5,4.6C81.6,11.6,79.6,13.6,77.1,13.6z">
                    </path>
                    <path
                        d="M65.1,11C55.4,0.9,51.2,0.4,49,0.4c-4.8,0-8.7,3.9-8.7,8.7c0,4.8,3.9,8.7,8.7,8.7c0.5,0,3.6,0.3,6.8-3.3 C59.5,10.2,65.1,11,65.1,11z M48.9,13.6c-2.5,0-4.5-2.1-4.5-4.6c0-2.5,2-4.6,4.5-4.6s4.5,2.1,4.5,4.6 C53.4,11.6,51.4,13.6,48.9,13.6z">
                    </path>
                </g>
            </g>
        </svg>
    </footer>
</body>

</html>
"""


@dataclass
class TimedText:
    speaker: str
    speaker_color: Optional[str]
    timestamp: timedelta
    sentence: str


FILLWORDS = ["the", "but", "say", "I"]


def parse_transcript_results(
    transcript_data: dict,
    include_disfluencies: bool = False,
    sentences_per_paragraph: int = 3,
) -> Iterator[TimedText]:
    for speaker, words in groupby(
        transcript_data["results"], lambda x: x["alternatives"][0]["speaker"]
    ):
        word_list = list(words)
        if not include_disfluencies:
            word_list = [
                w
                for w in word_list
                if "tags" not in w["alternatives"][0]
                or "disfluency" not in w["alternatives"][0]["tags"]
            ]
            # remove duplicate punctuation
            word_list = [
                w
                for i, w in enumerate(word_list)
                if i == 0
                or not (
                    w["type"] == "punctuation"
                    and word_list[i - 1]["type"] == "punctuation"
                )
            ]
            # remove duplicate fillwords after punctuation removed
            word_list = [
                w
                for i, w in enumerate(word_list)
                if i == 0
                or not (
                    w["alternatives"][0]["content"].lower() in FILLWORDS
                    and word_list[i - 1]["alternatives"][0]["content"].lower()
                    == w["alternatives"][0]["content"].lower()
                )
            ]

        paragraph_boundaries = [
            i + 1 for i, w in enumerate(word_list) if "is_eos" in w and w["is_eos"]
        ]
        paragraph_boundaries = paragraph_boundaries[::sentences_per_paragraph]
        # breakpoint()
        for paragraph_start, paragraph_end in zip(
            [0] + paragraph_boundaries, paragraph_boundaries
        ):
            partial_list = word_list[paragraph_start:paragraph_end]
            # breakpoint()
            if len(partial_list) == 0:
                continue
            text = join_tokens(
                partial_list,
                transcript_data["metadata"]["language_pack_info"]["word_delimiter"],
            )
            if text[0].islower():
                text = text[0].upper() + text[1:]
            start = partial_list[0]["start_time"]

            yield TimedText(
                speaker,
                speaker_color=None,
                timestamp=timedelta(seconds=round(start, 3)),
                sentence=text,
            )


def generate_html(
    transcript_data: List[TimedText], summary: Optional[str], title: Optional[str]
):
    template = Environment(loader=BaseLoader()).from_string(TEMPLATE)
    output = template.render(
        transcript_entries=transcript_data, summary=summary, title=title
    )

    print(output)


def process_transcript(
    transcript: Iterator[TimedText],
    speakers_to_discard: List[str],
    speaker_dict: Dict[str, str],
    word_replacements: Dict[str, str],
) -> Iterator[TimedText]:
    for t in transcript:
        if t.speaker in speakers_to_discard:
            continue

        id = int(t.speaker[1:]) - 1
        color = COLORS[id] if id < len(COLORS) else None
        speaker = speaker_dict.get(t.speaker, t.speaker)
        replaced_text = t.sentence
        for old, new in word_replacements.items():
            replaced_text = replaced_text.replace(old, new)
        yield TimedText(speaker, color, t.timestamp, replaced_text)


def main():
    ap = ArgumentParser()
    ap.add_argument("json_file", type=Path)
    ap.add_argument("--discard-speakers", nargs="+", type=str, default=[])
    ap.add_argument("--speakers", nargs="+", type=str, default=[])
    ap.add_argument("--title", type=str)
    ap.add_argument("--include-disfluencies", action="store_true")
    ap.add_argument("--max-sentences-per-paragraph", type=int, default=3)
    args = ap.parse_args()
    with args.json_file.open() as json_fh:
        transcript_data = json.load(json_fh)
    speaker_dict = {f"S{i+1}": speaker for i, speaker in enumerate(args.speakers)}
    transcript = parse_transcript_results(
        transcript_data, args.include_disfluencies, args.max_sentences_per_paragraph
    )
    summary = transcript_data.get("summary")
    summary = summary["content"] if summary else None
    generate_html(
        list(
            process_transcript(
                transcript, args.discard_speakers, speaker_dict, word_replacements={}
            )
        ),
        summary,
        args.title,
    )


if __name__ == "__main__":
    main()
